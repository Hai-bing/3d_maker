"""中→英提示词离线词典。

3D 生成场景下，常见物体/颜色/材质的中文对照表。
翻译逻辑优先走本词典（离线、确定、不受外部 API 波动影响），
避免中文直接喂给 SDXL 的英文 CLIP 导致语义错乱（如「椅子」生成「摩托车」）。
"""

# 键按「最长优先」匹配，避免短词误命中长词的前缀
DICT = {
    # ── 家具 / 家居 ──
    "椅子": "chair",
    "桌子": "table",
    "沙发": "sofa",
    "床": "bed",
    "柜子": "cabinet",
    "衣柜": "wardrobe",
    "书架": "bookshelf",
    "台灯": "table lamp",
    "吊灯": "chandelier",
    "落地灯": "floor lamp",
    "花瓶": "vase",
    "花盆": "flower pot",
    "镜子": "mirror",
    "钟": "clock",
    "闹钟": "alarm clock",
    "垃圾桶": "trash can",
    "衣架": "coat hanger",
    "鞋柜": "shoe cabinet",
    "茶几": "coffee table",
    "餐桌": "dining table",
    "办公桌": "office desk",
    "办公椅": "office chair",
    "板凳": "stool",
    "凳子": "stool",

    # ── 交通工具 ──
    "汽车": "car",
    "轿车": "sedan",
    "跑车": "sports car",
    "越野车": "SUV",
    "摩托车": "motorcycle",
    "自行车": "bicycle",
    "飞机": "airplane",
    "直升机": "helicopter",
    "轮船": "ship",
    "帆船": "sailboat",
    "火车": "train",
    "卡车": "truck",
    "公交车": "bus",

    # ── 餐具 / 厨具 ──
    "杯子": "cup",
    "茶杯": "teacup",
    "咖啡杯": "coffee mug",
    "马克杯": "mug",
    "碗": "bowl",
    "盘子": "plate",
    "碟子": "dish",
    "茶壶": "teapot",
    "水壶": "kettle",
    "锅": "pot",
    "平底锅": "frying pan",
    "刀": "knife",
    "叉": "fork",
    "勺子": "spoon",
    "筷子": "chopsticks",

    # ── 电子产品 ──
    "手机": "smartphone",
    "电脑": "computer",
    "笔记本电脑": "laptop",
    "键盘": "keyboard",
    "鼠标": "mouse",
    "显示器": "monitor",
    "电视": "television",
    "耳机": "headphones",
    "音箱": "speaker",
    "相机": "camera",
    "手表": "watch",
    "充电器": "charger",
    "台灯": "desk lamp",

    # ── 玩具 / 摆件 ──
    "玩具": "toy",
    "积木": "building blocks",
    "玩偶": "doll",
    "泰迪熊": "teddy bear",
    "公仔": "figurine",
    "手办": "action figure",
    "雕像": "statue",
    "雕塑": "sculpture",

    # ── 乐器 ──
    "吉他": "guitar",
    "钢琴": "piano",
    "小提琴": "violin",
    "鼓": "drum",
    "笛子": "flute",

    # ── 植物 ──
    "花": "flower",
    "树": "tree",
    "盆栽": "bonsai",
    "仙人掌": "cactus",
    "玫瑰": "rose",
    "向日葵": "sunflower",

    # ── 建筑 / 结构 ──
    "房子": "house",
    "城堡": "castle",
    "塔": "tower",
    "桥": "bridge",
    "亭子": "pavilion",
    "庙": "temple",
    "教堂": "church",

    # ── 衣物 / 配饰 ──
    "鞋子": "shoes",
    "靴子": "boots",
    "帽子": "hat",
    "包": "bag",
    "背包": "backpack",
    "眼镜": "glasses",
    "戒指": "ring",
    "项链": "necklace",
    "耳环": "earrings",
    "手链": "bracelet",

    # ── 其他常见物体 ──
    "球": "ball",
    "足球": "soccer ball",
    "篮球": "basketball",
    "灯笼": "lantern",
    "蜡烛": "candle",
    "书": "book",
    "笔": "pen",
    "铅笔": "pencil",
    "伞": "umbrella",
    "钥匙": "key",
    "锁": "lock",
    "箱子": "box",
    "篮子": "basket",
    "花瓶": "vase",

    # ── 颜色（形容词） ──
    "红色": "red",
    "蓝色": "blue",
    "绿色": "green",
    "黄色": "yellow",
    "黑色": "black",
    "白色": "white",
    "灰色": "gray",
    "粉色": "pink",
    "紫色": "purple",
    "橙色": "orange",
    "棕色": "brown",
    "金色": "golden",
    "银色": "silver",
    "青铜色": "bronze",
    "透明": "transparent",

    # ── 材质（形容词） ──
    "陶瓷": "ceramic",
    "瓷器": "porcelain",
    "玻璃": "glass",
    "木质": "wooden",
    "木头": "wood",
    "金属": "metal",
    "塑料": "plastic",
    "石头": "stone",
    "大理石": "marble",
    "皮革": "leather",
    "布料": "fabric",
    "毛绒": "plush",
    "不锈钢": "stainless steel",
    "混凝土": "concrete",
    "竹制": "bamboo",
    "竹子": "bamboo",

    # ── 风格 / 外观（形容词） ──
    "卡通": "cartoon style",
    "写实": "realistic",
    "可爱": "cute",
    "简约": "minimalist",
    "现代": "modern",
    "复古": "vintage",
    "古典": "classical",
    "奢华": "luxurious",
    "精致": "exquisite",
    "花纹": "pattern",
    "金色花纹": "golden pattern",
    "皮质": "leather",
    "带有": "with",
    "带": "with",
    "一个": "a",
    "一只": "a",
    "一对": "a pair of",
    "一盏": "a",
}


def translate_zh_to_en(text: str) -> str:
    """离线词典翻译：对词典中命中的中文片段替换为英文。

    按 key 长度降序匹配，优先替换长词（如「办公椅」优先于「椅子」）。
    替换后的英文词两侧补空格，避免多个词粘连（如「红色陶瓷」→「redceramic」）。
    未命中的中文片段原样保留，交由上层兜底。
    """
    # 按长度降序，保证长词先匹配
    for zh in sorted(DICT, key=len, reverse=True):
        if zh in text:
            text = text.replace(zh, f" {DICT[zh]} ")
    # 清理中文标点残留与多余空格
    for punct in "，。、；：！？（）【】":
        text = text.replace(punct, " ")
    return " ".join(text.split())
