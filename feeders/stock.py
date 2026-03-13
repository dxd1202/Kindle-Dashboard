import yfinance as yf
import os
import ast

# ================= 配置区 =================
# 从环境变量读取字符串，并用 ast 转换回 Python 列表对象
watchlist_raw = os.getenv("STOCK_LIST")
if watchlist_raw:
    WATCHLIST = ast.literal_eval(watchlist_raw)
else:
    WATCHLIST = []
# ==========================================

def get_stock_data(symbol, friendly_name):
    print(f"[股市模块] 正在获取 {friendly_name}({symbol}) 数据...")
    
    # 统一样式模板
    # ▷ 开启单行加粗但不渲染图标
    # ↓ 开启缩小模式
    # ○ 恢复默认
    style_template = "▷{name}○ ↓{detail}○"

    try:
        ticker = yf.Ticker(symbol)
        # 获取 7 天数据，增加拿到数据的概率（防止中间有节假日）
        hist = ticker.history(period="7d")
        
        # --- 核心改进：极其严格的防御性检查 ---
        if hist is None or hist.empty:
            return style_template.format(name=friendly_name, detail="无数据")

        # 拿到最新一行的价格
        current_price = hist['Close'].iloc[-1]
        
        # 自动判断货币符号
        currency = "¥" if (".SS" in symbol or ".SZ" in symbol) else "$"

        # 检查是否至少有 2 行数据来计算涨跌
        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            change_pct = (current_price - prev_close) / prev_close * 100
            arrow = "＋" if change_pct >= 0 else "－"
            detail_info = f"{currency}{current_price:.2f} ▷{arrow}{abs(change_pct):.1f}%○"
        else:
            # 如果只有一行数据，就只显示价格，不显示涨跌
            detail_info = f"{currency}{current_price:.2f}"
            
        return style_template.format(name=friendly_name, detail=detail_info)

    except Exception as e:
        print(f"[股市模块] {friendly_name} 抓取异常: {e}")
        # 即使失败也返回字符串，用于占位
        return style_template.format(name=friendly_name, detail="获取失败")

def update(config):
    info_parts = []
    
    for symbol, name in WATCHLIST:
        data_str = get_stock_data(symbol, name)
        # 无论成功失败，都加入列表
        info_parts.append(data_str)
    
    # 将列表按每行 2 个进行切片并用 \t 连接
    combined_lines = []
    for i in range(0, len(info_parts), 2):
        pair = info_parts[i : i + 2]
        # 使用制表符 \t 触发 C++ 的格子居中对齐逻辑
        combined_lines.append("\t".join(pair))
    
    # 最终合并成一段带换行的文本
    final_content = "\n".join(combined_lines)
    
    for item in config.get("widgets", []):
        if item.get("id") == "stock":
            item["content"] = final_content
            break
            
    return config