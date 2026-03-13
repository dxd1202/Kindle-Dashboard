import yfinance as yf

# ================= 配置区 =================
# 在这里定义你想看的资产：(代码, 显示名称)
WATCHLIST = [
    ("000001.SS", "上证指数"),
    ("399001.SZ", "深证成指"),
    ("000680.SS", "科创综指"),
    ("399006.SZ", "创业板指"),
    ("^IXIC", "纳斯达克"),
    ("^HSI", "香港恒生"),
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