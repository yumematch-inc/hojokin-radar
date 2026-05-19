#!/usr/bin/env python3
"""はなひらく 補助金レーダー 週次メール送信スクリプト"""
import json, re, urllib.request, urllib.error
from datetime import date, datetime

RESEND_API_KEY = "re_JffiedtX_GPxVM7NxmoEqFxgEPSa4mhEb"
FROM_EMAIL = "はなひらく補助金レーダー <noreply@hanahiraku-group.com>"
TO_EMAIL = "info@hanahiraku-group.com"
PORTAL_URL = "https://hanahiraku-portal-mzuq.vercel.app/hojokin"

# --- GRANTSデータをHTMLから抽出 ---
with open("index.html", encoding="utf-8") as f:
    html = f.read()

# GRANTS配列をJSから抽出してPythonで解析
m = re.search(r'const GRANTS = \[(.+?)\];\s*/\* ─── TAG', html, re.DOTALL)
raw = m.group(1)

# 各フィールドを正規表現で抽出
def extract_grants(raw):
    grants = []
    # 各grantブロックをid:Nで分割
    blocks = re.split(r'\s*\{\s*\n\s*id:', raw)
    for block in blocks:
        if not block.strip():
            continue
        g = {}
        def get(key, default=None):
            p = re.search(rf"{key}:'([^']*)'", block)
            if p: return p.group(1)
            p = re.search(rf'{key}:"([^"]*)"', block)
            if p: return p.group(1)
            return default
        id_m = re.match(r'(\d+)', block)
        if not id_m: continue
        g['id'] = int(id_m.group(1))
        g['title'] = get('title', '')
        g['amount'] = get('amount', '')
        g['deadlineLabel'] = get('deadlineLabel', '')
        dl = get('deadline')
        g['deadline'] = dl if dl and dl != 'null' else None
        # businesses
        bm = re.search(r"businesses:\[([^\]]+)\]", block)
        g['businesses'] = re.findall(r"'([^']+)'", bm.group(1)) if bm else []
        grants.append(g)
    return grants

grants = extract_grants(raw)

# はなひらく対象（businesses に hanahiraku か all が含まれるもの）
hana_grants = [g for g in grants if 'hanahiraku' in g['businesses'] or 'all' in g['businesses']]

# --- 締切日数計算 ---
today = date.today()

def days_left(deadline_str):
    if not deadline_str:
        return None
    try:
        d = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        return (d - today).days
    except:
        return None

def classify(g):
    d = days_left(g['deadline'])
    if d is None: return 'ongoing'
    if d < 0: return 'closed'
    if d <= 30: return 'urgent'
    if d <= 60: return 'warning'
    return 'normal'

for g in hana_grants:
    g['days'] = days_left(g['deadline'])
    g['status'] = classify(g)

# --- メールHTML生成 ---
today_str = today.strftime("%Y年%m月%d日")

def grant_item(g, cls=''):
    days_text = ''
    if g['status'] == 'ongoing':
        days_text = '<span style="color:#0d7a4b;font-weight:700;">通年申請可</span>'
    elif g['status'] == 'closed':
        days_text = '<span style="color:#999;">締切済み</span>'
    elif g['days'] is not None:
        days_text = f'<span style="font-weight:700;">残 {g["days"]}日</span>'

    border_colors = {'urgent': '#c81e1e', 'warning': '#c05621', 'ongoing': '#0d7a4b', 'normal': '#1a56db', 'closed': '#ccc'}
    bg_colors = {'urgent': '#fef8f8', 'warning': '#fffaf5', 'ongoing': '#f0fdf8', 'normal': '#f8faff', 'closed': '#fafafa'}
    bc = border_colors.get(g['status'], '#1a56db')
    bg = bg_colors.get(g['status'], '#f8faff')

    return f'''<div style="background:{bg};border-left:4px solid {bc};border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:8px;">
  <div style="font-weight:700;font-size:0.9rem;margin-bottom:4px;">{g["title"]}</div>
  <div style="font-size:0.8rem;color:#6b7a99;">{g["amount"]}</div>
  <div style="font-size:0.8rem;margin-top:4px;">{g["deadlineLabel"]}　{days_text}</div>
</div>'''

urgent_grants  = [g for g in hana_grants if g['status'] in ('urgent', 'warning')]
ongoing_grants = [g for g in hana_grants if g['status'] == 'ongoing']
all_items      = ''.join(grant_item(g) for g in hana_grants)
urgent_items   = ''.join(grant_item(g) for g in urgent_grants) if urgent_grants else '<p style="color:#999;font-size:0.85rem;">現在、60日以内の締切はありません。</p>'
ongoing_items  = ''.join(grant_item(g) for g in ongoing_grants)

html_body = f'''<!DOCTYPE html>
<html lang="ja">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:'Hiragino Sans',sans-serif;background:#f5f7fa;margin:0;padding:20px;color:#1a1a2e;">
<div style="max-width:640px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">

  <div style="background:linear-gradient(135deg,#0a2447,#1a56db);padding:32px 28px;color:#fff;">
    <div style="font-size:0.75rem;opacity:0.7;margin-bottom:8px;">はなひらくグループ 経営管理ポータル</div>
    <h1 style="font-size:1.3rem;margin:0 0 6px;">🌸 はなひらく 補助金・助成金レーダー</h1>
    <p style="font-size:0.85rem;opacity:0.8;margin:0;">週次レポート　／　{today_str}</p>
  </div>

  <div style="padding:20px 28px;border-bottom:1px solid #eef2f7;">
    <div style="font-size:0.75rem;font-weight:700;color:#6b7a99;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px;">🚨 締切間近・要注意（60日以内）</div>
    {urgent_items}
  </div>

  <div style="padding:20px 28px;border-bottom:1px solid #eef2f7;">
    <div style="font-size:0.75rem;font-weight:700;color:#6b7a99;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px;">✅ 通年・随時申請可（いつでもOK）</div>
    {ongoing_items}
  </div>

  <div style="padding:20px 28px;border-bottom:1px solid #eef2f7;">
    <div style="font-size:0.75rem;font-weight:700;color:#6b7a99;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px;">📋 全{len(hana_grants)}件サマリー</div>
    {all_items}
  </div>

  <div style="padding:24px 28px;text-align:center;border-bottom:1px solid #eef2f7;">
    <a href="{PORTAL_URL}" style="display:inline-block;background:#1a56db;color:#fff;padding:13px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:0.9rem;">ポータルで詳細を確認する →</a>
    <p style="font-size:0.78rem;color:#999;margin-top:10px;">必要書類・申請ステップは各カードで確認できます</p>
  </div>

  <div style="padding:20px 28px;background:#f8faff;font-size:0.75rem;color:#999;line-height:1.7;">
    このメールは毎週月曜7時に自動送信されています。<br>
    申請前に必ず各公式サイトで最新情報をご確認ください。
  </div>
</div>
</body></html>'''

# --- Resend API で送信 ---
subject = f"📡 補助金レーダー週次レポート（{today_str}）"
payload = json.dumps({
    "from": FROM_EMAIL,
    "to": [TO_EMAIL],
    "subject": subject,
    "html": html_body
}).encode("utf-8")

req = urllib.request.Request(
    "https://api.resend.com/emails",
    data=payload,
    headers={
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "python-resend/0.1"
    },
    method="POST"
)
try:
    with urllib.request.urlopen(req) as res:
        result = json.loads(res.read())
        print(f"送信成功: {result}")
except urllib.error.HTTPError as e:
    print(f"送信エラー {e.code}: {e.read().decode()}")
