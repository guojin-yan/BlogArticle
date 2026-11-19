"""Create small, attributable evidence figures from retained real run outputs."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(r'E:\GitSpace\ROCm-CSharp-Projects\runs')
OUT = ROOT / 'assets/evidence'
OUT.mkdir(exist_ok=True)
font_path = 'C:/Windows/Fonts/msyh.ttc'
font = ImageFont.truetype(font_path, 22)
small = ImageFont.truetype(font_path, 18)


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save_json(name, data):
    (ROOT / 'research/validation' / name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# An actual retained VisA input and model heatmap. Preserve the missed detection.
batch = SOURCE / 'industrial-inspection/batches/f466517249d84f5db5fc1f10d6cecc0d/03213ab94b8544b2a18a4570b725c122'
evaluation = SOURCE / 'industrial-inspection/evaluations/20261118-030919-1d02c103.json'
record = read(evaluation)
sample = next(item for item in record['samples'] if item['imageSha256'] == sha(batch / 'original.jpg'))
canvas = Image.new('RGB', (1280, 600), '#f5f7fb')
draw = ImageDraw.Draw(canvas)
draw.text((24, 14), 'SurfaceLab 实际保留结果：原图与异常热图', font=font, fill='#14243a')
for i, name in enumerate(['original.jpg', 'heatmap.png']):
    image = Image.open(batch / name).convert('RGB')
    image.thumbnail((600, 410))
    x = 24 + i * 632
    canvas.paste(image, (x + (600 - image.width) // 2, 65 + (410 - image.height) // 2))
    draw.text((x, 485), ['输入：VisA pcb1-anomaly-000', '模型异常热图：机器结果仍为漏检 FN'][i], font=small, fill='#14243a')
draw.text((24, 525), '已复用的 12 图流程检查：TP 3 / FN 3 / FP 0 / TN 6；不是独立质量验收。', font=small, fill='#9b3434')
draw.text((24, 559), '来源：Amazon Science VisA / spot-diff，CC BY 4.0；本图缩放并列展示原始产物。', font=small, fill='#586579')
canvas.save(OUT / 'surfacelab-real-result.png')
save_json('issue1-surfacelab-evidence.json', {
    'scope': 'Historical retained application output, not rerun in article task; reused 12-image flow check',
    'evaluationSha256': sha(evaluation), 'inputSha256': sha(batch / 'original.jpg'),
    'heatmapSha256': sha(batch / 'heatmap.png'), 'sample': sample,
    'confusion': record['confusion'], 'dataset': record['dataset'],
    'source': 'https://github.com/amazon-science/spot-diff', 'license': 'CC-BY-4.0',
    'transformation': 'Resized original input and retained heatmap side by side, labels added'})

# Authored video frames can be redistributed without copying public video media.
video = SOURCE / 'video-event-search/demo-v01-final/analysis'
record = read(video / 'result.json')
event = record['events'][0]
canvas = Image.new('RGB', (1280, 570), '#f5f7fb')
draw = ImageDraw.Draw(canvas)
draw.text((24, 15), 'VideoEventSearch 实际产物：候选事件与原始 PTS 回看', font=font, fill='#14243a')
for i, index in enumerate(event['evidenceFrames'][:2]):
    observation = next(item for item in record['observations'] if item['frameIndex'] == index)
    image = Image.open(video / f'frames/f{index:05d}.png').convert('RGB')
    image = image.resize((600, 360), Image.Resampling.NEAREST)
    x = 24 + i * 632
    canvas.paste(image, (x + (600-image.width)//2, 65 + (390-image.height)//2))
    time_base = record['timeBase']
    draw.text((x, 464), f"frame={index} / PTS={observation['pts']} / time_base={time_base['numerator']}/{time_base['denominator']}", font=small, fill='#14243a')
draw.text((24, 507), '作者编写的演示帧；zone-enter 候选需人工复核，不能据此给真实视频事件准确率。', font=small, fill='#9b3434')
canvas.save(OUT / 'video-pts-evidence.png')
save_json('issue1-video-evidence.json', {'scope':record['scope'], 'timeBase':record['timeBase'],
    'events':record['events'], 'observations':record['observations'], 'resultSha256':sha(video/'result.json'),
    'note':'Historical authored demo frames; not current trained-model event accuracy'})

ocr = SOURCE / 'document-evidence/paddleocr-en-v3-windows-v1/evaluation.json'
record = read(ocr)
save_json('issue1-document-evidence.json', {key:record.get(key) for key in
    ['startedAtUtc','finishedAtUtc','scope','backend','modelManifestSha256','manifestSha256','protocolSha256',
     'sampleCount','exactLines','exactLineAccuracy','characterErrorRate','maxAbsoluteReferenceError','failures']})

pcb2 = SOURCE/'industrial-inspection/evaluations/20261118-032028-8564ebd2.json'
record = read(pcb2)
save_json('issue1-surfacelab-quality.json', {'scope':'Historical pcb2 first category test; not rerun in article task',
    'evaluationSha256':sha(pcb2), **{key:record.get(key) for key in
    ['dataset','category','count','backend','confusion','precision','recall','falsePositiveRate','falseNegativeRate']},
    'examples': [next(s for s in record['samples'] if s['outcome']==kind) for kind in ['FP','FN']]})

# Standard plots for the actual newly executed CPU/HIP numerical experiment.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False
summary=read(ROOT/'research/validation/issue1-signal-comparison.json')
data={mode:read(ROOT/summary['reports'][mode]['path']) for mode in ['cpu','hip']}
frame={mode:r['frames'][40] for mode,r in data.items()}
fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.2), dpi=150)
for mode,label,color in [('cpu','CPU double reference','#295bb7'),('hip','HIP float32','#de6b34')]:
    s=frame[mode]['spectrum']
    axes[0].plot(s['frequencyHz'],s['psd'],label=label,color=color,lw=1.5,alpha=.8)
axes[0].set(xlim=(0,260),xlabel='Frequency (Hz)',ylabel='PSD ((arbitrary-unit)^2 / Hz)',title='实际窗口 40：CPU / HIP PSD')
axes[0].legend()
axes[1].bar(['CPU','HIP'],[15,15],color=['#295bb7','#de6b34'],width=.45)
axes[1].set(ylim=(0,20),ylabel='待复核窗口数 / 共 125 窗',title='同一输入与配置，逐窗决策一致')
for i in range(2): axes[1].text(i,15.4,'15',ha='center')
for ax in axes: ax.grid(axis='y',alpha=.15)
fig.suptitle('确定性演示信号：64 Hz + 2–3 秒的 192 Hz 成分；不代表设备故障准确率',fontsize=11)
fig.tight_layout()
fig.savefig(OUT/'signal-cpu-hip.png',bbox_inches='tight')
plt.close(fig)
print('Built actual application evidence figures and compact source records.')
