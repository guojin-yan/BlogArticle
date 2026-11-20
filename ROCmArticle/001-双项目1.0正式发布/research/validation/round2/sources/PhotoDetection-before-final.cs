using System.Diagnostics;
using System.Net;
using JYPPX.ROCm.HipSharp;
using JYPPX.ROCm.MIGraphXSharp;
using Microsoft.ML.OnnxRuntime;
using Microsoft.ML.OnnxRuntime.Tensors;
using StbImageSharp;
using StbImageWriteSharp;

static class PhotoDetection
{
    record Detection(int ClassId, string Label, float Score, float X1, float Y1, float X2, float Y2);
    public static int Run(string modelPath, string imagePath, string output)
    {
        var timer = Stopwatch.StartNew();
        using var imageStream = File.OpenRead(imagePath);
        var image = ImageResult.FromStream(imageStream, StbImageSharp.ColorComponents.RedGreenBlue);
        const int size = 416;
        double ratio = Math.Min((double)size / image.Width, (double)size / image.Height);
        int width = (int)(image.Width * ratio), height = (int)(image.Height * ratio);
        var input = Enumerable.Repeat(114f, 3 * size * size).ToArray();
        // YOLOX official preprocessing: top-left letterbox, BGR, [0,255], CHW.
        for (int y = 0; y < height; y++)
            for (int x = 0; x < width; x++)
            {
                double sx = Math.Clamp((x + .5) * image.Width / width - .5, 0, image.Width - 1);
                double sy = Math.Clamp((y + .5) * image.Height / height - .5, 0, image.Height - 1);
                int x0 = (int)sx, y0 = (int)sy, x1 = Math.Min(x0 + 1, image.Width - 1), y1 = Math.Min(y0 + 1, image.Height - 1);
                double wx = sx - x0, wy = sy - y0;
                for (int c = 0; c < 3; c++)
                {
                    int rgb = 2 - c;
                    double top = image.Data[(y0 * image.Width + x0) * 3 + rgb] * (1 - wx) + image.Data[(y0 * image.Width + x1) * 3 + rgb] * wx;
                    double bottom = image.Data[(y1 * image.Width + x0) * 3 + rgb] * (1 - wx) + image.Data[(y1 * image.Width + x1) * 3 + rgb] * wx;
                    input[c * size * size + y * size + x] = (float)Math.Round(top * (1 - wy) + bottom * wy);
                }
            }
        double decodePreprocessMs = timer.Elapsed.TotalMilliseconds;
        var probe = MIGraphXEnvironment.ProbeSystem();
        if (!probe.ObjectsExecuted) throw new InvalidOperationException("MIGraphX probe failed");
        string native = probe.LoadedPath!;
        using var hip = new HipRuntime(); hip.Initialize();
        using var options = new MIGraphXOnnxOptions(native);
        using var program = MIGraphXProgram.ParseOnnxBuffer(File.ReadAllBytes(modelPath), options);
        using var target = new MIGraphXTarget(native, "gpu");
        using var compile = new MIGraphXCompileOptions(native, offloadCopy: true, fastMath: false, exhaustiveTune: false);
        Console.WriteLine("Compiling YOLOX Nano for " + hip.GetDevices().First());
        timer.Restart(); program.Compile(target, compile); double compileMs = timer.Elapsed.TotalMilliseconds;
        var parameter = program.GetParameterShapes().Single();
        using var argument = MIGraphXArgument.Create(native, parameter.Value, input);
        using var map = new MIGraphXParameterMap(native); map.Add(parameter.Key, argument);
        timer.Restart();
        using var outputs = program.Run(map); hip.Synchronize();
        var values = outputs[0].ToArray<float>();
        double firstInferenceMs = timer.Elapsed.TotalMilliseconds;
        if (values.Length != 3549 * 85) throw new InvalidOperationException("Expected YOLOX Nano 416 raw grid output [1,3549,85]");
        using var cpu = new InferenceSession(modelPath);
        using var cpuOutput = cpu.Run(new[] { NamedOnnxValue.CreateFromTensor(parameter.Key, new DenseTensor<float>(input, new[] { 1, 3, size, size })) });
        var reference = cpuOutput.Single().AsTensor<float>().ToArray();
        int failed = values.Zip(reference).Count(p => !float.IsFinite(p.First) || !float.IsFinite(p.Second) || Math.Abs(p.First - p.Second) > .001 + .001 * Math.Abs(p.Second));
        if (failed != 0) throw new InvalidOperationException($"GPU vs CPU raw tensor: {failed} elements fail tolerance");
        var candidates = new List<Detection>();
        int index = 0;
        foreach (int stride in new[] { 8, 16, 32 })
            for (int gy = 0; gy < size / stride; gy++)
                for (int gx = 0; gx < size / stride; gx++, index++)
                {
                    int offset = index * 85;
                    int category = 0;
                    for (int c = 1; c < 80; c++) if (values[offset + 5 + c] > values[offset + 5 + category]) category = c;
                    float score = values[offset + 4] * values[offset + 5 + category];
                    if (score < .3f) continue;
                    double cx = (values[offset] + gx) * stride, cy = (values[offset + 1] + gy) * stride;
                    double bw = Math.Exp(values[offset + 2]) * stride, bh = Math.Exp(values[offset + 3]) * stride;
                    float X(double x) => (float)Math.Clamp(x / ratio, 0, image.Width - 1);
                    float Y(double y) => (float)Math.Clamp(y / ratio, 0, image.Height - 1);
                    candidates.Add(new(category, Labels[category], score, X(cx - bw / 2), Y(cy - bh / 2), X(cx + bw / 2), Y(cy + bh / 2)));
                }
        var detections = new List<Detection>();
        foreach (var item in candidates.OrderByDescending(x => x.Score))
            if (!detections.Any(kept => kept.ClassId == item.ClassId && IoU(kept, item) > .45f)) detections.Add(item);
        byte[] rendered = (byte[])image.Data.Clone();
        foreach (var item in detections)
        {
            for (int y = (int)item.Y1; y <= (int)item.Y2; y++)
                for (int x = (int)item.X1; x <= (int)item.X2; x++)
                    if (x - item.X1 < 3 || item.X2 - x < 3 || y - item.Y1 < 3 || item.Y2 - y < 3)
                    {
                        int p = (y * image.Width + x) * 3;
                        rendered[p] = 255; rendered[p + 1] = 45; rendered[p + 2] = 30;
                    }
        }
        string dir = Path.GetDirectoryName(Path.GetFullPath(output))!; Directory.CreateDirectory(dir);
        string renderedPath = Path.Combine(dir, "yolox-detections.png");
        using (var stream = File.Create(renderedPath))
            new ImageWriter().WritePng(rendered, image.Width, image.Height, StbImageWriteSharp.ColorComponents.RedGreenBlue, stream);
        Round2Tools.Write(output, new { date = DateTimeOffset.Now, device = hip.GetDevices().First().ToString(), native,
            modelSha256 = Round2Tools.Hash(modelPath), imageSha256 = Round2Tools.Hash(imagePath), resultImageSha256 = Round2Tools.Hash(renderedPath),
            originalWidth = image.Width, originalHeight = image.Height, ratio, threshold = .3, nmsIoU = .45,
            preprocessing = "STB RGB decode; bilinear integer-rounded resize; BGR [0,255]; top-left 114 letterbox; CHW 416",
            decoding = "YOLOX raw grid; exp(w,h)*stride; objectness*best-class; class-aware greedy NMS; coordinates divided by letterbox ratio",
            decodePreprocessMs, compileMs, firstInferenceMs, rawCompared = values.Length, failedElements = failed, nonFiniteElements = values.Count(x => !float.IsFinite(x)),
            maxAbs = values.Zip(reference).Max(p => Math.Abs((double)p.First - p.Second)), detections,
            status = "FUNCTIONAL DEMO; no independent annotations or mAP; not the synthetic benchmark" });
        string rows = string.Join("", detections.Select(d => $"<tr><td>{d.Label}</td><td>{d.Score:F4}</td><td>{d.X1:F1}, {d.Y1:F1}, {d.X2:F1}, {d.Y2:F1}</td></tr>"));
        string svg = string.Join("", detections.Select(d => $"<text x='{d.X1:F1}' y='{Math.Max(18,d.Y1-6):F1}' fill='#ff2d1e' stroke='white' stroke-width='.5' font-size='18'>{d.Label} {d.Score:F3}</text>"));
        File.WriteAllText(Path.Combine(dir, "detection-report.html"), $$"""
        <!doctype html><meta charset="utf-8"><title>YOLOX Nano — real W7900 result</title>
        <style>body{margin:30px auto;max-width:1100px;font:17px/1.6 Segoe UI,sans-serif;background:#f4f6fa;color:#18243b}h1{margin-bottom:4px}.images{display:flex;gap:24px}.images>div{width:50%}img{width:100%}.result{position:relative}svg{position:absolute;left:0;top:0;width:100%;height:100%}table{width:100%;text-align:left}td{padding:8px;border-bottom:1px solid #ccc}small{color:#526077}</style>
        <h1>YOLOX Nano · AMD W7900</h1><p>Real photograph → C# preprocessing → MIGraphX GPU → decode + NMS</p>
        <div class="images"><div><b>Original · NASA / Eileen Collins</b><img src="../inputs/astronaut.png"></div><div><b>Actual software output</b><div class="result"><img src="yolox-detections.png"><svg viewBox="0 0 {{image.Width}} {{image.Height}}">{{svg}}</svg></div></div></div>
        <table><tr><th>Class</th><th>Score</th><th>Original image box (xyxy)</th></tr>{{rows}}</table>
        <p>Raw GPU / ORT CPU: {{values.Length}} elements, {{failed}} failures · conf ≥ 0.30 · class-aware NMS IoU 0.45</p>
        <small>Functional demonstration; no mAP claim. Source: NASA public-domain astronaut photo via scikit-image. Boxes and scores are generated by the actual C# application; no AI-generated UI or predictions.</small>
        """);
        foreach (var item in detections) Console.WriteLine($"{item.Label} {item.Score:F4}: [{item.X1:F1},{item.Y1:F1},{item.X2:F1},{item.Y2:F1}]");
        Console.WriteLine($"PASS: full photo pipeline; {detections.Count} detections; raw GPU/CPU failures={failed}");
        return 0;
    }
    static float IoU(Detection a, Detection b)
    {
        float intersection = Math.Max(0, Math.Min(a.X2, b.X2) - Math.Max(a.X1, b.X1)) * Math.Max(0, Math.Min(a.Y2, b.Y2) - Math.Max(a.Y1, b.Y1));
        float union = (a.X2 - a.X1) * (a.Y2 - a.Y1) + (b.X2 - b.X1) * (b.Y2 - b.Y1) - intersection;
        return union > 0 ? intersection / union : 0;
    }
    static readonly string[] Labels = "person,bicycle,car,motorcycle,airplane,bus,train,truck,boat,traffic light,fire hydrant,stop sign,parking meter,bench,bird,cat,dog,horse,sheep,cow,elephant,bear,zebra,giraffe,backpack,umbrella,handbag,tie,suitcase,frisbee,skis,snowboard,sports ball,kite,baseball bat,baseball glove,skateboard,surfboard,tennis racket,bottle,wine glass,cup,fork,knife,spoon,bowl,banana,apple,sandwich,orange,broccoli,carrot,hot dog,pizza,donut,cake,chair,couch,potted plant,bed,dining table,toilet,tv,laptop,mouse,remote,keyboard,cell phone,microwave,oven,toaster,sink,refrigerator,book,clock,vase,scissors,teddy bear,hair drier,toothbrush".Split(',');
}
