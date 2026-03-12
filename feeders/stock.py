import yfinance as yf

# ================= 配置区 =================
# 在这里定义你想看的资产：(代码, 显示名称)
WATCHLIST = [
    ("510330.SS", "沪深300华夏"),
    ("513100.SS", "纳斯达克华泰"),
    ("513130.SS", "恒生科技华泰"),
    ("588000.SS", "科创50华夏"),
    ("515220.SS", "煤炭华泰"),
    ("513350.SS", "标普油气富国"),
    ("518880.SS", "黄金华安"),
    ("516510.SS", "云计算易方达"),
]
# ==========================================

def get_stock_data(symbol, friendly_name):
    print(f"[股市模块] 正在获取 {friendly_name}({symbol}) 数据...")
    try:
        ticker = yf.Ticker(symbol)
        # 获取 5 天数据以防遇到周末/节假日（确保能拿到最近两个交易日）
        hist = ticker.history(period="5d")
        
        if hist.empty:
            return None

        # 拿到最近两个交易日的收盘价
        current_price = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        change_pct = (current_price - prev_close) / prev_close * 100
        
        # 自动判断货币符号
        currency = "¥" if (".SS" in symbol or ".SZ" in symbol) else "$"
        arrow = "+" if change_pct >= 0 else "-"
        
        # --- 利用 C++ 渲染引擎的控制符 ---
        # ▷ 开启加粗（用于名称）
        # ↓ 缩小（用于价格和涨跌幅）
        # ○ 重置大小
        return f"{friendly_name} {currency}{current_price:.2f} {arrow}{abs(change_pct):.2f}%"

    except Exception as e:
        print(f"[股市模块] {friendly_name} 获取失败: {e}")
        return None

def update(config):
    info_parts = []
    
    for symbol, name in WATCHLIST:
        data_str = get_stock_data(symbol, name)
        if data_str:
            info_parts.append(data_str)
    
    # 拼接最终字符串。利用 \t 和我们在 C++ 里写的居中/对齐逻辑
    # 我们可以每行放 2 个资产，用 \n 换行
    combined_info = ""
    for i in range(0, len(info_parts), 2):
        pair = info_parts[i : i + 2]
        combined_info += "\t".join(pair) + "\n"
    
    # 更新 JSON
    for item in config.get("widgets", []):
        if item.get("id") == "stock":
            item["content"] = combined_info.strip()
            break
            
    return config