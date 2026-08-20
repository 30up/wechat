import akshare as ak
import pandas as pd
import requests
import datetime
import warnings
warnings.filterwarnings("ignore")

# 公众号配置，从环境变量读取
WECHAT_APPID = os.environ.get("WECHAT_APPID")
WECHAT_APPSECRET = os.environ.get("WECHAT_APPSECRET")

def get_wechat_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WECHAT_APPID}&secret={WECHAT_APPSECRET}"
    res = requests.get(url).json()
    return res["access_token"]

def get_stock_data():
    # 获取A股全部行情
    df = ak.stock_zh_a_spot_em()
    # 过滤条件
    # 剔除北交所
    df = df[~df["代码"].str.match(r"^8")]
    # 剔除ST
    df = df[~df["名称"].str.contains("ST", na=False)]
    # 剔除停牌：涨跌幅为空或者0
    df = df[df["涨跌幅"].notna()]
    df = df[df["涨跌幅"] != 0]

    df = df.copy()
    df["涨跌幅"] = pd.to_numeric(df["涨跌幅"])

    # 计算中位数
    median_pct = round(df["涨跌幅"].median(), 2)

    up_count = len(df[df["涨跌幅"]>0])
    down_count = len(df[df["涨跌幅"]<0])
    limit_up = len(df[df["涨跌幅"]>=9.8])
    limit_down = len(df[df["涨跌幅"]<=-9.8])

    # 获取指数
    index_df = ak.stock_zh_index_spot()
    sh = index_df[index_df["代码"]=="000001"]["涨跌幅"].iloc[0]
    hs300 = index_df[index_df["代码"]=="000300"]["涨跌幅"].iloc[0]

    return {
        "median": median_pct,
        "up": up_count,
        "down": down_count,
        "limit_up": limit_up,
        "limit_down": limit_down,
        "sh": round(sh,2),
        "hs300": round(hs300,2)
    }

def build_html(data):
    today = datetime.date.today().strftime("%Y‑%m‑%d")
    html = f"""
<h2>📊 A股盘后市场统计｜{today}</h2>
<p>🔹全A涨跌幅中位数：<strong>{data['median']}%</strong></p>
<p>📈上涨家数：{data['up']}｜📉下跌家数：{data['down']}</p>
<p>🚀涨停：{data['limit_up']}｜💥跌停：{data['limit_down']}</p>
<br>
<p>指数对照：</p>
<ul>
<li>上证指数：{data['sh']}%</li>
<li>沪深300：{data['hs300']}%</li>
</ul>
<br>
<p>💡说明：中位数为剔除ST、停牌、北交所后，全部A股涨跌幅排序取中间值。一半股票表现优于该数值，一半弱于它，不受权重股干扰。</p>
<p>⚠️风险提示：以上数据仅供复盘参考，不构成任何投资建议。</p>
"""
    return html

def send_wechat_article(token, html):
    title = f"📊盘后市场统计｜{datetime.date.today()}"
    # 上传图文素材接口
    url = "https://api.weixin.qq.com/cgi-bin/material/add_news?access_token="+token
    payload = {
        "articles": [{
            "title": title,
            "author": "",
            "digest": f"全A中位数：{data['median']}%｜上涨{data['up']}家，下跌{data['down']}家",
            "content": html,
            "show_cover_pic": 0
        }]
    }
    res = requests.post(url, json=payload).json()
    media_id = res["media_id"]

    # 群发接口
    send_url = "https://api.weixin.qq.com/cgi-bin/message/mass/sendall?access_token="+token
    send_data = {
        "filter": {"is_to_all": True},
        "mpnews": {"media_id": media_id},
        "msgtype": "mpnews",
        "send_ignore_reprint": 0
    }
    resp = requests.post(send_url, json=send_data).json()
    print(resp)

if __name__ == "__main__":
    data = get_stock_data()
    html = build_html(data)
    token = get_wechat_token()
    send_wechat_article(token, html)
