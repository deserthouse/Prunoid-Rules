# -*- coding: utf-8 -*-
"""
[存档副本] 本脚本的运行依赖主项目的 research/ 提取物目录，独立仓库内不可直接执行。
端侧快照由主项目生成后发布到 rules/snapshot.json；本副本用于审计生成逻辑。

Prunoid 冷启动快照构建脚本（M1-R2）
正源与协议（见 2026-09-17_数据源合规与建库原则.md）：
  1. blocker-general-rules (Apache-2.0)   —— SDK 禁用规则 468 条（含 safeToBlock/sideEffect/contributors），正源
  2. LibChecker-Rules v44  (Apache-2.0)   —— 组件级识别锚点（四类组件 + native so），骨架
  3. Fuck.AD dex 提取物（客观事实）        —— 16 家聚合广告 SDK 根包名
  4. oF2pks/3xodusprivacy-toolbox（无协议，仅事实）—— 包名前缀补充（低置信度）
红线：Exodus ODbL 数据不进快照；GPL/AGPL/无协议源的文件与文案不复制（oF2pks 只取名称/包名事实字段）。
输出：app/src/main/assets/rules/snapshot.json（自建 schema，逐条带 source/confidence）
"""
import json, glob, os, re, hashlib
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LCR = os.path.join(ROOT, "research", "lcr_repo")
BLOCKER = os.path.join(ROOT, "research", "blocker_rules_repo", "rules", "en", "general.json")
OF2PKS = os.path.join(ROOT, "research", "of2pks_toolbox", "trackers448NEW.txt")
OUT_DIR = os.path.join(ROOT, "app", "src", "main", "assets", "rules")

# Fuck.AD v3.0.6 dex 提取的 16 家聚合广告 SDK 根包名（调研报告增补一 §B2，客观事实）
FUCKAD_ROOTS = [
    ("Pangle 穿山甲", "ByteDance", "com.bytedance.sdk.openadsdk"),
    ("GDT 优量汇", "Tencent", "com.qq.e.ads"),
    ("Baidu 百青藤", "Baidu", "com.baidu.mobads.sdk.api"),
    ("Kwai 快手联盟", "Kuaishou", "com.kwad.sdk"),
    ("TopOn", "AnyThink", "com.anythink"),
    ("TradPlus", "TradPlus", "com.tradplus.ads"),
    ("Sigmob", "Sigmob", "com.sigmob"),
    ("Mintegral", "Mintegral", "com.mbridge.msdk"),
    ("AppLovin MAX", "AppLovin", "com.applovin.mediation"),
    ("Unity Ads", "Unity", "com.unity3d.ads"),
    ("Unity Services Ads", "Unity", "com.unity3d.services.ads"),
    ("Vungle", "Liftoff", "com.vungle.ads"),
    ("IronSource", "Unity", "com.ironsource.sdk"),
    ("Qumeng 趣盟", "Qumeng", "com.qumeng.advlib"),
    ("Douban Ad", "Douban", "com.douban.ad"),
    ("Windmill 风车", "WindMill", "com.windmill.sdk"),
]

CAT_RULES = [
    (re.compile(r"广告|Ad[s]? SDK|Ads$|Advertising|Monetization|聚合|联盟广告|穿山甲|优量汇|百青藤|开屏|Pangle|CSJ|GroMore|AdMob|AdColony|Inmobi|IronSource|Vungle|Mintegral|Mbridge|AppLovin|Unity Ads|Sigmob|TopOn|AnyThink|TradPlus|Windmill|AdsWizz|SmartAd|Adform|Adaptive|Mediation|Monetize|Ads Kit|Mobvista|Audience Network|应用推广", re.I), "ads"),
    (re.compile(r"推送|Push|JPush|极光|个推|Getui|信鸽|XG Push|MiPush|小米推送|HMS Push|FCM|GCM|OneSignal|Pushwoosh|Airship|巴法云|友盟推送|TPush|云推送|MCS", re.I), "push"),
    (re.compile(r"统计|分析|Analytics|Statistics|Tracking|Tracker|Attribution|测量|埋点|AppsFlyer|Adjust|Branch|Kochava|Sensors|神策|GrowingIO|友盟|Umeng|Flurry|Amplitude|Mixpanel|Braze|CleverTap|Localytics|mParticle|Segment|Tealium|Comscore|Nielsen|Appsflyer|数说|TalkingData|热云|Tracking", re.I), "analytics"),
    (re.compile(r"崩溃|Crash|性能|Performance|APM|监控|Monitoring|Bugly|Crashlytics|Sentry|Fresco|FIR|Bugtags|Instabug|xCrash|Matrix|APM|Flipper", re.I), "quality"),
    (re.compile(r"登录|分享|Share|Login|Account|OAuth|支付|Pay|微信|微博|QQ互联|新浪|支付宝|银联|OneTap|Auth|Stripe|TapTap|TapSDK", re.I), "social_or_pay"),
    (re.compile(r"地图|Location|定位|Map|BaiduMap|AMap|高德|腾讯地图|Geofence|Beacon|蓝牙|BLE|NFC|Wi-Fi 扫描", re.I), "maps"),
    (re.compile(r"云|存储|Storage|数据库|Database|下载|Download|Update|升级|热修|Hotfix|Sophix|Tinker|Robust|网络|Network|OkHttp|Retrofit|Volley|Cronet|加速|CDN|直播|Live|播放器|Player|RTC|IM|推送通道|WebView|Chaquopy|Python|浏览服务|TBS|VirtualApp|VirtualAPK|Sobot|智齿|Qiyukf|七鱼", re.I), "infra"),
    (re.compile(r"安全|风控|Security|Risk|反作弊|Anti-|加固|Bangcle|360加固|梆梆|爱加密|Verify|Device ID|设备指纹|Fingerprint|Shumei|数美|同盾|TongDun|实人认证|人脸|核身|RealIdentity|Face Verify", re.I), "security"),
    (re.compile(r"androidx|Jetpack|Kotlin|Coroutines|Google Play|Play Services|Guava|gRPC|Protobuf|Firebase(?! Analytics)|WorkManager|Room|Compose|Lifecycle|Startup|Profile|HMS Core", re.I), "framework"),
]

# 批R5 数据侧：跨语言别名 → 规范名（与规则库 name 全等匹配）
ALIAS_MERGES = {
    # 批R5 基础三对
    "Aurora Push": "极光推送",
    "Getui SDK": "个推",
    "JiGuang Aurora Mobile JPush": "极光推送",
    # 批H（2026-09-26）：判定书 docs/alias_decisions.md，共 14 对
    "Pangle 穿山甲": "Pangle SDK",
    "Pangolin Advertising SDK": "Pangle SDK",
    "AppLovin": "AppLovin MAX",
    "Huawei Ads SDK": "HUAWEI Ads Kit",
    "Jetpack Camera2": "Jetpack Camera",
    "Ali Mobile push": "阿里移动推送",
    "Tencent Mobile Push": "腾讯移动推送",
    "Unity3d Ads": "Unity Ads",
    "Liftoff Monetize": "Vungle",
    "Google CrashLytics": "Google Crashlytics",
    "Android Beacon Library": "AltBeacon",
    "Google Ads": "Google AdMob",
    "Oppo Advertising Alliance": "OPPO 广告 SDK",
    "Huawei Mobile Services (HMS) Core Library": "Huawei Mobile Services (HMS) Core",
    # 批H 第二批（设备实测+过宽前缀扫描出土）
    "Pangle": "Pangle SDK",
    "AppLovin (MAX and SparkLabs)": "AppLovin MAX",
    "Twitter MoPub": "MoPub Ads",
    "TopOn": "TopOn SDK",
    "SAP CDC (Gigya)": "Gigya",
    # 批H 第三批（2026-09-26 收尾：双名独占域扫描 27 对 + Mobvista 联网定案）
    "Adjust SDK": "Adjust",
    "Ali TBAuth": "Ali Account SDK",
    "金融级实人认证 SDK": "Aliyun DTF Face Verify",
    "实人认证 SDK": "Aliyun RealIdentity",
    "AutoNavi / Amap": "高德地图 SDK",
    "Baidu Cloud Push": "百度云推送",
    "Bugly": "Tencent Bugly",
    "DataFinder analysis": "DataFinder",
    "Facebook Flipper": "Flipper",
    "HMS Core Ads SDK": "HUAWEI Ads Kit",
    "Honor Ad Alliance": "荣耀广告 SDK",
    "Jetpack Media Session": "Jetpack Media3",
    "Kuaishou Advertising Alliance": "快手广告 SDK",
    "Kwai 快手联盟": "快手广告 SDK",
    "Mapbox Maps SDK": "Mapbox",
    "Sobot Chat SDK": "智齿客服 SDK",
    "Stripe Payments": "Stripe SDK",
    "TapSDK": "TapTap 开发者服务",
    "Tencent Browser Service (X5 Kernel)": "腾讯浏览服务（TBS）",
    "Tencent Mobile Analytics": "腾讯移动分析",
    "Tinker": "Tencent Tinker hot update",
    "Umeng Push Platform": "友盟推送",
    "VirtualAPK Framework": "VirtualAPK",
    "VirtualApp Framework": "VirtualApp",
    "Vivo message push service": "vivo Push",
    "Xiaomi Mobile Ads Alliance (Mimo Ad SDK)": "小米广告 SDK",
    "人脸核身 SDK": "Tencent Face Verification (Huiyan)",
    "Mobvista": "Mintegral",
    # 批T1（2026-10-10）：长尾清账 10 对，判定书 docs/alias_decisions.md H 节
    "GDT 优量汇": "腾讯广告 SDK",
    "Unity Services Ads": "Unity Ads",
    "Audience Network SDK": "Audience Network",
    "移动应用推广 SDK": "Baidu 百青藤",
    "七鱼 SDK": "NetEase Qiyukf",
    "Umeng Analytics": "移动统计分析",
    "Baidu Face Recognition": "百度人脸识别",
    "Baidu Maps": "百度地图 SDK",
    "Xiaomi Push": "MiPush",
    "网易云通信 SDK": "网易云信",
}
NAME_CATEGORY_MAP = {
    # ── 广告/变现/联盟 ──
    "Teemo": "ads", "FidZup": "ads", "Ad4Screen": "ads", "Weborama": "ads",
    "OutBrain": "ads", "Widespace": "ads", "AppNexus": "ads", "S4M": "ads",
    "Sizmek": "ads", "Sync2Ad": "ads", "Nexage": "ads", "Ogury Presage": "ads",
    "Add Apt Tr": "ads", "Vectaury": "ads", "Moat": "ads",
    "Glispa Connect (Formerly Avocarrot)": "ads", "Shopkick": "ads",
    "Alphonso": "ads", "Millennial Media": "ads", "myTarget": "ads",
    "Yandex Ad": "ads", "Rubicon Project": "ads", "Fiksu": "ads",
    "AdFit (Daum)": "ads", "Adot": "ads", "AppMonet": "ads", "Soomla": "ads",
    "Adincube": "ads", "Criteo": "ads", "Taboola": "ads", "Cloudmobi": "ads",
    "ADLIB": "ads", "InMarket": "ads", "Appnext": "ads", "MobFox": "ads",
    "ShallWeAD": "ads", "HyprMX": "ads", "Duapps": "ads", "AerServ": "ads",
    "Tapjoy": "ads", "Kiip": "ads", "MobPower": "ads", "AdBuddiz": "ads",
    "Integral Ad Science": "ads", "nend": "ads", "FreeWheel": "ads",
    "TNK Factory": "ads", "Axonix": "ads", "YouAppi": "ads", "Tapdaq": "ads",
    "Verve": "ads", "Revmob": "ads", "Altamob": "ads", "AMoAd": "ads",
    "AdAdapted": "ads", "AdMuing": "ads", "Adcash": "ads", "Admost": "ads",
    "AdFalcon": "ads", "adPOPcorn": "ads", "POKKT": "ads", "Prebid Mobile": "ads",
    "BidMachine": "ads", "BuzzAd Benefit": "ads", "GOM Factory AdPie": "ads",
    "LoopMe": "ads", "SuperAwesome": "ads", "Tappx": "ads",
    "AdGateMedia": "ads", "AdMarvel": "ads", "Snap Ad Kit": "ads",
    "Vdopia": "ads", "AdGem": "ads", "AdTrial": "ads", "Pincrux": "ads",
    "Yoadx": "ads", "BeiZi SDK": "ads", "ADSuyi SDK": "ads",
    "Honor Ad Alliance": "ads", "腾讯流量联盟": "ads", "京媒 SDK": "ads",
    "Facebook advertisement": "ads", "WeChat advertisement": "ads",
    "Bilibili advertisement": "ads", "Amazon Advertisement": "ads",
    "Amazon Mobile Associates": "ads", "Baidu Mobile App Promotion": "ads",
    "Signal360": "ads", "Instreamatic (Adman)": "ads", "Auditude": "ads",
    "Ad Generation": "ads", "Adjoe": "ads", "TeleQuid": "ads",
    "Lisnr": "ads", "GPShopper": "ads", "OfferToro": "ads", "Geniee": "ads",
    "YuMe": "ads", "Zapr": "ads", "mediba": "ads", "Conversant": "ads",
    "Amobee": "ads", "Metaps": "ads", "Pollfish": "ads",
    # ── 统计/归因/数据 ──
    "HockeyApp": "analytics", "LeanPlum": "analytics", "ATInternet": "analytics",
    "Xiti": "analytics", "Snowplow": "analytics", "Webtrends": "analytics",
    "Quantcast": "analytics", "AppMetrica": "analytics", "Webtrekk": "analytics",
    "Chartbeat": "analytics", "Parse.ly": "analytics", "INFOnline": "analytics",
    "OzTAM": "analytics", "Twine Data": "analytics", "Alohalytics": "analytics",
    "AppSee": "analytics", "UXCam": "analytics", "Repro": "analytics",
    "Heap": "analytics", "CoolaData": "analytics", "Alooma": "analytics",
    "MoEngage": "analytics", "Swrve": "analytics", "Keen": "analytics",
    "Metrics": "analytics", "Reveal Mobile": "analytics", "Sensoro": "analytics",
    "Sense360": "analytics", "Areametrics": "analytics", "OpenLocate": "analytics",
    "PredicIO": "analytics", "mTraction": "analytics", "Databox": "analytics",
    "Treasure Data": "analytics", "Insider": "analytics", "Mopinion": "analytics",
    "Wootric": "analytics", "Emarsys Predict": "analytics", "Lotame": "analytics",
    "Demdex": "analytics", "BlueKai (acquired by Oracle)": "analytics",
    "BlueConic": "analytics", "ExactTarget": "analytics", "Omniture": "analytics",
    "Eulerian": "analytics", "TagCommander (Commanders Act.)": "analytics",
    "Ensighten": "analytics", "Cuebiq": "analytics", "Factual": "analytics",
    "Footmarks": "analytics", "Sentiance": "analytics", "Pyze": "analytics",
    "Placer": "analytics", "LotaData": "analytics", "Huq Sourcekit": "analytics",
    "X-Mode": "analytics", "SignalFrame": "analytics", "Colocator": "analytics",
    "deltaDNA": "analytics", "Adbrix": "analytics", "Apsalar": "analytics",
    "Singular": "analytics", "Tenjin": "analytics", "Tapstream": "analytics",
    "Tune": "analytics", "Mobile Engagement": "analytics",
    "1DS": "analytics", "Tencent MTA": "analytics", "Tencent Stats": "analytics",
    "腾讯灯塔 DataTalk": "analytics", "腾讯灯塔 SDK": "analytics",
    "腾讯灯塔终端 ID 精准识别体系": "analytics", "Baidu Mobile Stat": "analytics",
    "Ali Mobile Data Analysis": "analytics", "Huawei DTM": "analytics",
    "Google Tag Manager": "analytics", "Foresee": "analytics",
    "Qualtrics": "analytics", "Tamoco": "analytics", "Opensignal": "analytics",
    "Unacast Pure": "analytics", "FLUZO": "analytics", "MOCA": "analytics",
    "Synerise": "analytics", "Cedexis Radar": "analytics", "Insider": "analytics",
    "MDOTM": "analytics", "AppLink.io": "analytics", "Askingpoint": "analytics",
    # ── 质量/稳定性 ──
    "Bugsnag": "quality", "Bugsee": "quality", "BugSense": "quality",
    "Buglife": "quality", "Apteligent by VMWare (formerly Crittercism)": "quality",
    "ACRA": "quality", "LeakCanary": "quality", "KOOM": "quality",
    "App Center": "quality", "Critic": "quality", "Acrarium": "quality",
    "FlowUp": "quality", "CodeLocator": "quality", "HWCPipe": "quality",
    "PerfGenius": "quality", "HardCoder": "quality",
    # ── 推送/触达 ──
    "Facebook Notifications": "push", "OtherLevels": "push", "Pulsate": "push",
    "OpenBack": "push",
    # ── 社交/支付/账号 ──
    "VKontakte SDK": "social_or_pay", "Ping++ SDK": "social_or_pay",
    "米大师": "social_or_pay", "天翼账号认证": "social_or_pay",
    "号码认证服务": "social_or_pay", "移动号码认证": "social_or_pay",
    "闪验 SDK": "social_or_pay", "一键登录和本机号码校验": "social_or_pay",
    "华为账号服务": "social_or_pay", "欢太账号授权 SDK": "social_or_pay",
    "欢太账号 OAuth 授权 SDK": "social_or_pay", "WeChat NFC": "social_or_pay",
    "小米账号开放平台": "social_or_pay", "招商银行 SDK": "social_or_pay",
    # ── 地图/定位 ──
    "百度 LBS": "maps", "百度 Navigation": "maps", "Baidu Navigation": "maps",
    "Baidu Location": "maps", "Baidu Map": "maps", "wgs2gcj": "maps",
    "Esri ArcGIS": "maps", "Carto (formerly Nutiteq)": "maps",
    "IndoorAtlas": "maps", "Point Inside": "maps", "Locuslabs": "maps",
    "Radar": "maps", "Glympse": "maps", "Herow": "maps", "In Loco": "maps",
    "Kontakt": "maps", "Bluecats": "maps",
    # ── 安全/风控/反作弊 ──
    "防水墙": "security", "网易易盾": "security",
    "网易易盾智能反外挂": "security", "AppSealing": "security",
    "APKiD": "security", "RootBeer": "security", "IPQualityScore": "security",
    "Akamai Bot Manager": "security", "Jumio": "security", "Acuant": "security",
    "Threadfix": "security", "数字联盟可信 ID SDK": "security",
    "MSA SDK": "security", "AntiFakerAndroidChecker": "security",
    "手游安全 SDK": "security", "腾讯云手游安全": "security",
    "Didomi": "security", "Lenddo": "security", "PairIP": "security",
    # ── 框架/账号体系级 ──
    "Unity": "framework", "ARCore": "framework", "Cardboard SDK": "framework",
    "ML Kit": "framework", "HMS ML Kit": "framework", "Facebook SDK": "framework",
    "Google Sign-In": "framework", "OSS Licenses Gradle Plugin": "framework",
    "Google Cast": "framework", "File Provider": "framework", "multidex": "framework",
    "HMS Core": "framework", "HMS Core AAID": "framework", "HMS Health Kit": "framework",
    "HMS Scan Kit": "framework", "HMS Video Kit": "framework",
    "HMS Audio Kit": "framework", "HMS Business Touch Kit": "framework",
    "AppGallery Connect": "framework", "HUAWEI CaaS Engine": "framework",
    "MSAL": "framework", "ADAL": "framework", "Intune App SDK": "framework",
    "Weex": "framework", "uni-app": "framework", "Hippy": "framework",
    "Lynx": "framework", "FinClip": "framework", "ArkUI-X": "framework",
    "Taro": "framework", "Kraken": "framework", "GaiaX": "framework",
    "Solar2D (Corona)": "framework", "GameMaker Studio": "framework",
    "LayaAir": "framework",
    # ── 基础设施/网络/存储/插件化/媒体 ──
    "AgentWeb": "infra", "Bolts": "infra", "Bitly": "infra", "Enhance": "infra",
    "BoostMultiDex": "infra", "RePlugin": "infra", "DRouter": "infra",
    "Qigsaw": "infra", "Neptune": "infra", "Android-Job": "infra",
    "rn-fetch-blob": "infra", "ShadowHook": "infra", "BHook": "infra",
    "xHook": "infra", "Dobby": "infra", "Sandhook": "infra", "Epic": "infra",
    "Pine": "infra", "SHook": "infra", "FreeReflection": "infra",
    "AnySDK": "infra", "DexKit": "infra", "DexPatch": "infra", "AndFix": "infra",
    "Linphone": "infra", "PJSIP": "infra", "OpenTok": "infra",
    "Mediastreamer2": "infra", "乐播 SDK": "infra", "实时音视频": "infra",
    "GME": "infra", "游戏语音 GVoice": "infra", "即构极速视频 SDK": "infra",
    "小鱼易联终端 SDK": "infra", "JusTalk Cloud": "infra", "AnyChat": "infra",
    "ObjectBox": "infra", "Realm": "infra", "SQLCipher": "infra",
    "MongoDB": "infra", "OpenSSL": "infra", "BoringSSL": "infra",
    "Conscrypt": "infra", "LibCurl": "infra", "cJSON": "infra",
    "UniRapidJson": "infra", "aria2": "infra", "libaria2": "infra",
    "bsdiff": "infra", "bspatch": "infra", "HDiffPatch": "infra", "hsynz": "infra",
    "Minilzo": "infra", "Zstandard": "infra", "libdeflate": "infra",
    "unrar-android": "infra", "AndroidP7zip": "infra", "Un7zip": "infra",
    "AndroidUtilCode": "infra", "libfuse": "infra",
    "gocryptsfs": "infra", "Sodium": "infra", "Argon2": "infra",
    "lib-encrypt": "infra", "HevSocks5Tunnel": "infra", "sing-box": "infra",
    "Xray Core": "infra", "tun2proxy": "infra", "Tun2Socks": "infra",
    "OpenVPN": "infra", "quiche": "infra", "TQUIC": "infra", "XQUIC": "infra",
    "rhttp": "infra", "ENet": "infra", "libp2p": "infra",
    "xnn": "infra", "XNet": "infra", "Mars": "infra", "WCDB": "infra",
    "libuv": "infra", "OpenCC": "infra", "OpenCC 开放中文转换": "infra",
    "iconv": "infra", "pcre2": "infra", "glog": "infra", "Logan": "infra",
    "Log4a": "infra", "Log for C++": "infra", "logging": "infra",
    "Termux": "infra", "Shizuku": "infra", "Rclone": "infra",
    "dav1d": "infra", "libheif": "infra", "libmpeg2": "infra", "x264": "infra",
    "ogg": "infra", "Opus": "infra", "Vorbis": "infra",
    "Free Lossless Audio Codec": "infra", "LAME": "infra", "SoundTouch": "infra",
    "Speex": "infra", "opencore-amr": "infra", "ffavc": "infra",
    "MediaInfoLib": "infra", "AVPro Video": "infra",
    "Anvato (A Google Company)": "infra",
    "libpng": "infra", "libjpeg-turbo": "infra", "LibJPEG": "infra",
    "LibRaw": "infra", "libYUV": "infra", "libhfyuv": "infra", "Lib_XUL": "infra",
    "FreeType": "infra", "Liblouis": "infra", "LibVLC": "infra", "LibMpv": "infra",
    "SkiaSharp": "infra", "libGDX": "infra", "GL4ES": "infra", "MobileGlues": "infra",
    "Virocore": "infra", "LWJGL": "infra", "Micro3D": "infra", "Rive": "infra",
    "Vulkan Validation Layers": "infra", "angle": "infra", "libchrome": "infra",
    "V8": "infra", "QuickJS": "infra", "QuickJS Binding": "infra",
    "J2V8": "infra", "PuerTS": "infra", "Node.js": "infra", "Golang": "infra",
    "KDE Framework": "infra", "LibOMP": "infra", "libtcc": "infra",
    "android-tree-sitter": "infra", "Lexbor": "infra", "Cello": "infra",
    "Process Phoenix": "infra", "RUpgrade": "infra", "EasyFloat": "infra",
    "FloatingX": "infra", "ReToast": "infra", "AndroidAutoSize": "infra",
    "Matisse": "infra", "PictureSelector": "infra",
    "Dexter": "infra", "EasyPermissions": "infra", "AndPermission": "infra",
    "Backendless": "infra", "Split": "infra",
    # ── AI/机器学习/计算机视觉 ──
    "OpenCV": "infra", "ncnn": "infra", "MNN": "infra", "TNN": "infra",
    "MindSpore Lite": "infra", "LiteRT": "infra", "Executorch": "infra",
    "Paddle Lite": "infra", "SNPE SDK": "infra", "FastCV": "infra",
    "MediaPipe Tasks": "infra", "MediaPipe LLM Inference": "infra",
    "Ascend CANN": "infra", "Arcsoft": "infra", "Faceunity Nama SDK": "infra",
    "旷视 SDK": "infra", "人像美化 SDK": "infra", "讯飞 SDK": "infra",
    "星火认知大模型": "infra", "思必驰": "infra", "语音识别 SDK": "infra",
    "离线语音合成": "infra", "离线语音合成 SDK": "infra", "AIUI": "infra",
    "Krisp AI 语音 SDK": "infra", "speechEngine": "infra", "vad": "infra",
    "Vosk": "infra", "文字识别服务": "infra", "Leptonica": "infra",
    "Tesseract": "infra",

}

def categorize(name):
    for pat, cat in CAT_RULES:
        if pat.search(name):
            return cat
    # 批T3：长尾显式归类表兜底
    return NAME_CATEGORY_MAP.get(name, "other")

def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

sdks = {}   # merge_key -> rule dict
comps = {}  # merge_key -> list of {type, class}

def put(key, name, company, cat, prefixes, safe, side, sources, confidence, contributors):
    r = sdks.get(key)
    if r is None:
        sdks[key] = {
            "id": hashlib.md5(key.encode()).hexdigest()[:12],
            "name": name, "company": company, "category": cat,
            "packPrefixes": sorted(set(prefixes)),
            "safeToBlock": safe, "sideEffect": side or "",
            "sources": sources, "confidence": confidence,
            "contributors": contributors[:6],
        }
        comps[key] = []
    else:
        r["packPrefixes"] = sorted(set(r["packPrefixes"]) | set(prefixes))
        for s in sources:
            if s not in r["sources"]:
                r["sources"].append(s)
        if confidence == "high" and r["confidence"] != "high":
            r["confidence"] = "high"
        r["contributors"] = list(dict.fromkeys(r["contributors"] + contributors))[:6]
    return key

# ── 1. blocker-general-rules（正源，Apache-2.0）────────────────────
n_blocker = 0
for r in jload(BLOCKER):
    put(f"blocker:{r['name']}", r["name"], r.get("company", ""),
        categorize(r["name"]), r.get("searchKeyword", []),
        bool(r.get("safeToBlock", False)), r.get("sideEffect", ""),
        ["blocker-general-rules(Apache-2.0)"], "high",
        r.get("contributors", []))
    n_blocker += 1

# ── 2. Fuck.AD 16 家根包名（dex 逆向事实）─────────────────────────
n_fuckad = 0
for name, company, root in FUCKAD_ROOTS:
    put(f"fuckad:{root}", name, company, "ads", [root],
        False, "", ["Fuck.AD v3.0.6 dex(facts)"], "medium", [])
    n_fuckad += 1

# ── 3. LibChecker-Rules v44 组件锚点（Apache-2.0）─────────────────
def lcr_locale_meta(path):
    d = jload(path)
    zh = en = None
    for loc in d.get("data", []):
        if loc.get("locale") == "zh-Hans": zh = loc.get("data", {})
        elif loc.get("locale") == "en": en = loc.get("data", {})
    return zh or en or {}

comp_count = 0
TYPE_MAP = [("activities-libs", "activity"), ("services-libs", "service"),
            ("receivers-libs", "receiver"), ("providers-libs", "provider")]
for dirname, ctype in TYPE_MAP:
    for p in glob.glob(os.path.join(LCR, dirname, "**", "*.json"), recursive=True):
        rel = os.path.relpath(p, os.path.join(LCR, dirname))[:-5].replace("\\", "/")
        cls = rel.replace("/", ".")
        meta = lcr_locale_meta(p)
        label = meta.get("label") or cls.rsplit(".", 1)[0]
        team = meta.get("dev_team", "")
        key = put(f"lcr:{label}", label, team, categorize(label), [],
                  False, "", ["LibChecker-Rules v44(Apache-2.0)"], "high",
                  meta.get("rule_contributors", []))
        comps[key].append({"type": ctype, "class": cls})
        comp_count += 1
# native so：锚点 = 文件名（如 chaquopy.so）；regex/ 子目录无模式字段，跳过
so_count = 0
for p in glob.glob(os.path.join(LCR, "native-libs", "*.json")):
    so_name = os.path.basename(p)[:-5]
    meta = lcr_locale_meta(p)
    label = meta.get("label") or so_name
    key = put(f"lcrso:{label}", label, meta.get("dev_team", ""),
              categorize(label), [],
              False, "", ["LibChecker-Rules v44(Apache-2.0)"], "high",
              meta.get("rule_contributors", []))
    comps[key].append({"type": "native", "class": so_name})
    so_count += 1

# ── 4. oF2pks 补充索引（无协议，仅名称/包名事实，低置信度）────────
n_of2pks = 0
if os.path.exists(OF2PKS):
    with open(OF2PKS, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("____")
            if len(parts) < 2:
                continue
            name = re.sub(r"^[µ°²?]+", "", parts[0]).strip()
            prefix = parts[1].strip()
            if not name or not prefix or len(prefix) < 5:
                continue
            key = put(f"of2pks:{prefix}", name, "", categorize(name), [prefix],
                      False, "", ["oF2pks/3xodusprivacy-toolbox(facts)"], "low", [])
            n_of2pks += 1

# ── 输出 ──────────────────────────────────────────────────────────
out = {
    "schemaVersion": 1,
    "aliases": ALIAS_MERGES,
    "generatedAt": datetime.now().isoformat(timespec="seconds"),
    "generator": "scripts/build_snapshot.py",
    "license": "Apache-2.0 (sources: blocker-general-rules, LibChecker-Rules; facts: Fuck.AD dex, oF2pks index)",
    "stats": {"sdks": len(sdks), "blocker": n_blocker, "fuckad": n_fuckad,
              "lcrComponents": comp_count, "lcrSo": so_count, "of2pks": n_of2pks},
    "sdks": [],
}
for key, r in sdks.items():
    r["components"] = comps[key]
    out["sdks"].append(r)

os.makedirs(OUT_DIR, exist_ok=True)
outp = os.path.join(OUT_DIR, "snapshot.json")
with open(outp, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print(f"sdks={len(sdks)} blocker={n_blocker} fuckad={n_fuckad} lcrComp={comp_count} lcrSo={so_count} of2pks={n_of2pks}")
print(f"size={os.path.getsize(outp)/1024:.0f}KB -> {os.path.relpath(outp, ROOT)}")
