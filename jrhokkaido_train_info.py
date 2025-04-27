"""
JR 北海道運行情報 MCP サーバー
"""

from mcp.server.fastmcp import FastMCP, Image
from mcp.server.fastmcp.prompts import base
import logging
import sys
from typing import Dict, List, Optional, Union
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import os
import pathlib

# ────────────────── ロガー設定（stderr 出力） ──────────────────
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ────────────────── MCP 初期化 ──────────────────
mcp = FastMCP("JR北海道列車運行情報", log_level="INFO")
log.info("MCP サーバー初期化完了")

# ────────────────── 共通定数 ──────────────────
# JR北海道の運行情報ページURLマップ
AREA_URLS = {
    # ローマ字コード
    "sapporo": "https://www3.jrhokkaido.co.jp/webunkou/area_spo.html",
    "doo": "https://www3.jrhokkaido.co.jp/webunkou/area_doo.html",
    "donan": "https://www3.jrhokkaido.co.jp/webunkou/area_donan.html",
    "dohoku": "https://www3.jrhokkaido.co.jp/webunkou/area_dohoku.html",
    "doto": "https://www3.jrhokkaido.co.jp/webunkou/area_doto.html",
    "shinkansen": "https://www3.jrhokkaido.co.jp/webunkou/senku.html?id=24",
    # 漢字表記
    "札幌": "https://www3.jrhokkaido.co.jp/webunkou/area_spo.html",
    "札幌近郊": "https://www3.jrhokkaido.co.jp/webunkou/area_spo.html",
    "道央": "https://www3.jrhokkaido.co.jp/webunkou/area_doo.html",
    "道南": "https://www3.jrhokkaido.co.jp/webunkou/area_donan.html",
    "道北": "https://www3.jrhokkaido.co.jp/webunkou/area_dohoku.html",
    "道東": "https://www3.jrhokkaido.co.jp/webunkou/area_doto.html",
    "北海道新幹線": "https://www3.jrhokkaido.co.jp/webunkou/senku.html?id=24",
    "新幹線": "https://www3.jrhokkaido.co.jp/webunkou/senku.html?id=24",
}
REQUEST_TIMEOUT = 10  # 秒

# ────────────────── 共通関数 ──────────────────
async def fetch_train_info(url: str) -> str:
    """JR北海道運行情報ページのHTMLを取得"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=REQUEST_TIMEOUT) as response:
            response.raise_for_status()
            return await response.text()

async def scrape_area(url: str) -> List[Dict]:
    """エリアページから遅延情報をスクレイプ"""
    html = await fetch_train_info(url)
    soup = BeautifulSoup(html, "html.parser")
    
    results = []
    
    # todayGaikyo div内のgaikyo-listを探索
    gaikyo_div = soup.find("div", id="todayGaikyo")
    if not gaikyo_div:
        log.warning(f"todayGaikyo div not found in {url}")
        return results
        
    gaikyo_list = gaikyo_div.find("ul", class_="gaikyo-list")
    if not gaikyo_list:
        log.warning(f"gaikyo-list not found in todayGaikyo div in {url}")
        return results
    
    # リスト内の各項目を取得
    list_items = gaikyo_list.find_all("li")
    for item in list_items:
        item_text = item.text.strip()
        
        # 「遅れに関する情報はありません」などの場合はスキップ
        if "遅れに関する情報はありません" in item_text or "情報はありません" in item_text:
            continue
            
        # 遅延カテゴリの判定
        category = "other"
        if any(word in item_text for word in ["遅延", "Delay"]):
            category = "delay"
        elif any(word in item_text for word in ["運休", "Suspension", "Suspend"]):
            category = "suspension"
        elif any(word in item_text for word in ["お知らせ", "Notice"]):
            category = "notice"
        
        # URL中のエリア名から路線名を推定
        line_name = "不明"
        if "area_spo" in url:
            line_name = "札幌近郊"
        elif "area_doo" in url:
            line_name = "道央"
        elif "area_donan" in url:
            line_name = "道南"
        elif "area_dohoku" in url:
            line_name = "道北"
        elif "area_doto" in url:
            line_name = "道東"
        elif "senku.html" in url and "id=24" in url:
            line_name = "北海道新幹線"
            
        results.append({
            "line": line_name,
            "status": item_text,
            "category": category
        })
        
    return results

# ────────────────── MCP ツール ──────────────────
@mcp.tool()
async def get_delays(area: Optional[str] = None) -> Dict:
    """JR北海道の遅延情報を取得
    
    Args:
        area: 取得するエリア ("札幌"/"sapporo", "道央"/"doo", "道南"/"donan", "道北"/"dohoku", "道東"/"doto", "北海道新幹線"/"shinkansen")。省略時は全エリア取得
    """
    areas = [area] if area else list(AREA_URLS.keys())
    all_results = []
    
    for a in areas:
        if a not in AREA_URLS:
            all_results.append({
                "area": a, 
                "line": "", 
                "status": "", 
                "category": "other", 
                "error": f"Unknown area: {a}"
            })
            continue
            
        try:
            url = AREA_URLS[a]
            results = await scrape_area(url)
            for r in results:
                all_results.append({"area": a, **r})
        except Exception as exc:
            log.exception(f"{a}エリアの遅延情報取得エラー")
            all_results.append({
                "area": a, 
                "line": "", 
                "status": "", 
                "category": "other", 
                "error": f"{exc}"
            })
    
    text = "遅延情報がありません。" if not all_results else "\n".join(
        f"[{r['area']}] ERROR: {r['error']}" if 'error' in r else f"[{r['area']}] {r['line']}: {r['status']}"
        for r in all_results
    )
    
    return {"content": [{"type": "text", "text": text}]}

# ────────────────── MCP プロンプト ──────────────────
@mcp.prompt()
def check_all_areas() -> str:
    """全エリアの運行状況を確認するプロンプト"""
    return """JR北海道の全エリア（札幌近郊、道央、道南、道北、道東、北海道新幹線）の運行状況を確認して、遅延や運休があれば詳細を教えてください。情報がない場合はその旨を伝えてください。"""

@mcp.prompt()
def check_specific_area(area: str) -> str:
    """特定エリアの運行状況を確認するプロンプト
    
    Args:
        area: 確認したいエリア名 (例: "札幌", "道央", "道南", "道北", "道東", "北海道新幹線")
    """
    return f"""JR北海道の{area}エリアの運行状況を確認して、遅延や運休があれば詳細を教えてください。情報がない場合はその旨を伝えてください。"""

@mcp.prompt()
def delay_impact_analysis() -> list[base.Message]:
    """JR北海道の遅延状況を分析するプロンプト"""
    return [
        base.UserMessage("""JR北海道の全路線の遅延情報を取得して、以下の点について分析してください：

1. 現在どのエリアで最も多くの遅延が発生していますか？
2. どのような種類の遅延（運休・遅延・その他）が多いですか？
3. 札幌駅を起点として移動する場合、現時点で最も影響の少ないルートはどこですか？

できるだけ詳細な情報で分析をお願いします。"""),
        base.AssistantMessage("JR北海道の運行状況を分析します。お待ちください..."),
    ]

# ────────────────── エントリーポイント ──────────────────
def start_server():
    """MCPサーバーを開始する関数"""
    try:
        log.info("利用可能ツール: %s", [get_delays.__name__])
        log.info("利用可能プロンプト: %s", [
            check_all_areas.__name__, 
            check_specific_area.__name__, 
            delay_impact_analysis.__name__
        ])
        log.info("クライアントからの接続を待機中…")
        mcp.run(transport="stdio")
    except Exception:
        log.exception("致命的エラーによりサーバーを終了します")
        raise

if __name__ == "__main__":
    start_server()
else:
    # モジュールとしてインポートされた場合でもサーバーを起動
    start_server()