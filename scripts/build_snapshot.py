# -*- coding: utf-8 -*-
"""
Prunoid-Rules 快照构建脚本（批K 归一版，2026-10-22）
自 research/ 私有管线归一公开（records/batch_K_plan_2026-10-22.md K1-K3）：
v1~v12 由主仓 research/build_snapshot.py 生成（README 历史声明），v13 起由本脚本
生成并在 CI 完成 tag 冻结重建 byte 级校验（scripts/rebuild_check 在 CI 内联执行）。

正源与协议（主仓 2026-09-17_数据源合规与建库原则.md）：
  1. blocker-general-rules (Apache-2.0)   —— SDK 禁用规则（含 safeToBlock/sideEffect/contributors），正源
  2. LibChecker-Rules      (Apache-2.0)   —— 组件级识别锚点（四类组件 + native so），骨架
  3. Fuck.AD dex 提取物（客观事实）        —— 16 家聚合广告 SDK 根包名（脚本内常量）
  4. oF2pks/3xodusprivacy-toolbox（无协议，仅事实）—— 包名前缀补充（低置信度；只取名称/包名字段，
     其文件不复制入库——CI 从上游固定 commit 拉取，pin 见 scripts/upstream_pins.json）
红线：Exodus ODbL 数据不进快照；GPL/AGPL/无协议源的文件与文案不复制。
输出：自建 schema JSON，逐条带 sources/confidence，可溯源。

确定性（批K K2）：--freeze-at 固定 generatedAt；全部 glob 排序+组件终排序——同输入
同字节，跨平台可复现（v13 起成立；v12 及以前的历史产物含未排序 glob 的平台序，不做回溯）。
构建环境约束（2026-10-22 实证）：官方构建环境=Linux（CI）。上游 LibChecker-Rules 存在
大小写碰撞文件（native-libs/libMuPDF.so.json 与 libmupdf.so.json 并存），Windows 大小写
不敏感文件系统检出只剩其一——Windows 本地构建会少 1 条 native 锚点，不得作为发布来源。
"""
import argparse
import glob
import hashlib
import json
import os
import re
from datetime import datetime

# Fuck.AD v3.0.6 dex 提取的 16 家聚合广告 SDK 根包名（主仓调研报告增补一 §B2，客观事实）
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
    # 2026-09-18 扩充批（UNKNOWN 回填）：词表来源=快照 UNKNOWN/other 桶词频实证（仅品牌名事实）
    (re.compile(r"Appodeal|Fyber|Ligatus|Madvertise|Cauly|Vpon|TapResearch|Chartboost|Smaato|PubMatic|OpenX|AdsNative|AdMix|AdTech|AdNetwork|Yandex Ads|StartApp|AirPush|LeadBolt|AppBrain|Adfurikun|Akamai Ads|MoPub|Flurry Ads|Heyzap|Union Ads|内嵌广告|Reward", re.I), "ads"),
    (re.compile(r"推送|Push|JPush|极光|个推|Getui|信鸽|XG Push|MiPush|小米推送|HMS Push|FCM|GCM|OneSignal|Pushwoosh|Airship|巴法云|友盟推送|TPush|云推送|MCS", re.I), "push"),
    (re.compile(r"统计|分析|Analytics|Statistics|Tracking|Tracker|Attribution|测量|埋点|AppsFlyer|Adjust|Branch|Kochava|Sensors|神策|GrowingIO|友盟|Umeng|Flurry|Amplitude|Mixpanel|Braze|CleverTap|Localytics|mParticle|Segment|Tealium|Comscore|Nielsen|Appsflyer|数说|TalkingData|热云|Tracking", re.I), "analytics"),
    (re.compile(r"FullStory|Telemetry|Matomo|Piwik|Exponea|Acoustic|Marketing Cloud|Measurement|CleanInsights|Countly|Pendo|Amplitude|Horizon|Datafinder|Audience|Batch|Persona|Gigya|Janrain|Kinesis|Plausible|Fathom|Woopra|Kissmetrics|Mouseflow|Smartlook|Trace", re.I), "analytics"),
    (re.compile(r"崩溃|Crash|性能|Performance|APM|监控|Monitoring|Bugly|Crashlytics|Sentry|Fresco|FIR|Bugtags|Instabug|xCrash|Matrix|APM|Flipper", re.I), "quality"),
    (re.compile(r"Dynatrace|Loggly|Splunk|Datadog|NewRelic|New Relic|AppDynamics|Raygun|Rollbar|TrackJS|Uptime", re.I), "quality"),
    (re.compile(r"登录|分享|Share|Login|Account|OAuth|支付|Pay|微信|微博|QQ互联|新浪|支付宝|银联|OneTap|Auth|Stripe|TapTap|TapSDK", re.I), "social_or_pay"),
    (re.compile(r"地图|Location|定位|Map|BaiduMap|AMap|高德|腾讯地图|Geofence|Beacon|蓝牙|BLE|NFC|Wi-Fi 扫描", re.I), "maps"),
    (re.compile(r"HyperTrack|Radario|GeoUniq|PathSense|Pilgrim", re.I), "maps"),
    (re.compile(r"云|存储|Storage|数据库|Database|下载|Download|Update|升级|热修|Hotfix|Sophix|Tinker|Robust|网络|Network|OkHttp|Retrofit|Volley|Cronet|加速|CDN|直播|Live|播放器|Player|RTC|IM|推送通道|WebView|Chaquopy|Python|浏览服务|TBS|VirtualApp|VirtualAPK|Sobot|智齿|Qiyukf|七鱼", re.I), "infra"),
    (re.compile(r"ZXing|SQLite|MMKV|Fcitx|ReLinker|Glide|Coil|Picasso|Lottie|ExoPlayer|FFmpeg|Zip|Brotli|Zstd|WebP|SVG|Pdf|Barcode|Scanner|Camera|Image|Crop|Compress|Archiver|Native|Cpp|Java|Kotlin", re.I), "infra"),
    (re.compile(r"安全|风控|Security|Risk|反作弊|Anti-|加固|Bangcle|360加固|梆梆|爱加密|Verify|Device ID|设备指纹|Fingerprint|Shumei|数美|同盾|TongDun|Reinforcement|Shield|Guard|Protect|实人认证|人脸|核身|RealIdentity|Face Verify", re.I), "security"),
    (re.compile(r"androidx|Jetpack|Kotlin|Coroutines|Google Play|Play Services|Guava|gRPC|Protobuf|Firebase(?! Analytics)|WorkManager|Room|Compose|Lifecycle|Startup|Profile|HMS Core", re.I), "framework"),
    (re.compile(r"React Native|Flutter|Expo|Xamarin|Capacitor|Cordova|Ionic|Unity Engine|Unreal|Cocos|Godot|Defold|Mono|IL2CPP|DotNet|MAUI", re.I), "framework"),
]

# 批R5/H：跨语言别名 → 规范名（运行时 RuleDedup 消费，保守合并锚点并集；
# 判定书=rules-repo docs/alias_decisions.md 与主仓 docs 同步副本）
ALIAS_MERGES = {
    # 批R5 基础三对
    "Aurora Push": "极光推送",
    "Getui SDK": "个推",
    "JiGuang Aurora Mobile JPush": "极光推送",
    # 批GG-G2（2026-10-21）：百度 mobads 系三实体同族（oF2pks com.baidu.mobads /
    # blocker com.baidu.mobads. / Fuck.AD com.baidu.mobads.sdk.api 均指百青藤移动广告）
    "Baidu Mobile Ads": "Baidu 百青藤",
    "Baidu Mobile App Promotion": "Baidu 百青藤",
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
    # 批T1（2026-10-10）：长尾清账 10 对，判定书 docs/alias_decisions.md H 节（rules-repo 同步副本）
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
    # 批DD（2026-10-20，LCR 2026-10-16 增量 71 实体归类）
    "Agora AOSL": "infra",
    "BMF": "infra",
    "ByteVC1 Encoder": "infra",
    "ByteVC2 Decoder": "infra",
    "Cash Raven": "ads",
    "CoreCLR": "infra",
    "Dart JNI": "framework",
    "DataDome": "security",
    "Djinni": "framework",
    "GGML": "infra",
    "Google Mobile Ads Next-Gen SDK": "ads",
    "Google Places SDK for Android": "maps",
    "Json.NET": "infra",
    "LiteRT-LM": "infra",
    "MaaFramework": "framework",
    "Microsoft Clarity": "analytics",
    "MobileGL": "infra",
    "OpenCV Face Detection Sample": "infra",
    "Screeb": "analytics",
    "SignatureKillerEx": "security",
    "Spectrum": "quality",
    "irondash Engine Context": "framework",
    "llama.rn": "infra",
    "open_file": "framework",
    "sherpa-onnx": "infra",
    "slua": "framework",
    "xDL": "quality",
    "天玑倍帧 SDK": "quality",
    "火山引擎点播 SDK": "infra",
    "迅雷 SDK": "infra",

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

def sglob(pattern, recursive=False):
    """确定性 glob（批K K2）：路径排序——跨平台字节可复现的前提（原生 glob 顺序为 OS 序）。"""
    return sorted(glob.glob(pattern, recursive=recursive))

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

def build(lcr, blocker_json, of2pks_txt, freeze_at, generator):
    # ── 1. blocker-general-rules（正源，Apache-2.0）────────────────────
    n_blocker = 0
    for r in jload(blocker_json):
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

    # ── 3. LibChecker-Rules 组件锚点（Apache-2.0）─────────────────────
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
        for p in sglob(os.path.join(lcr, dirname, "**", "*.json"), recursive=True):
            rel = os.path.relpath(p, os.path.join(lcr, dirname))[:-5].replace("\\", "/")
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
    for p in sglob(os.path.join(lcr, "native-libs", "*.json")):
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
    if of2pks_txt and os.path.exists(of2pks_txt):
        with open(of2pks_txt, encoding="utf-8") as f:
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

    # ── 5. 富描述回填（b5 管线固化，2026-09-18）：LCR 组件 JSON 自带 description/dev_team/source_link ──
    # 按组件锚点回填 + 同名规则互播；描述取 zh-Hans 优先、en 兜底
    def _enrich_key(key, meta):
        r = sdks.get(key)
        if r is None or not meta:
            return False
        desc = meta.get("description", "")
        if desc and not r.get("description"):
            r["description"] = desc
            r["devTeam"] = meta.get("dev_team", "")
            r["sourceLink"] = meta.get("source_link", "")
            return True
        return False

    enriched = 0
    for dirname, ctype in TYPE_MAP:
        for p in sglob(os.path.join(lcr, dirname, "**", "*.json"), recursive=True):
            rel = os.path.relpath(p, os.path.join(lcr, dirname))[:-5].replace("\\", "/")
            cls = rel.replace("/", ".")
            d = jload(p)
            zh = en = None
            for loc in d.get("data", []):
                if loc.get("locale") == "zh-Hans": zh = loc.get("data", {})
                elif loc.get("locale") == "en": en = loc.get("data", {})
            # 描述可能只存在于单一 locale：逐语言取
            meta = {}
            for m in (zh, en):
                if not m: continue
                meta.setdefault("description", m.get("description", ""))
                meta.setdefault("dev_team", m.get("dev_team", ""))
                meta.setdefault("source_link", m.get("source_link", ""))
            if not meta.get("description"):
                continue
            for key, cl in comps.items():
                if any(c["class"] == cls for c in cl):
                    if _enrich_key(key, meta):
                        enriched += 1
                    break
    # native so：描述同样逐文件取（b5 覆盖主力）
    for p in sglob(os.path.join(lcr, "native-libs", "*.json")):
        so_name = os.path.basename(p)[:-5]
        d = jload(p)
        zh = en = None
        for loc in d.get("data", []):
            if loc.get("locale") == "zh-Hans": zh = loc.get("data", {})
            elif loc.get("locale") == "en": en = loc.get("data", {})
        meta = {}
        for m in (zh, en):
            if not m: continue
            meta.setdefault("description", m.get("description", ""))
            meta.setdefault("dev_team", m.get("dev_team", ""))
            meta.setdefault("source_link", m.get("source_link", ""))
        if not meta.get("description"):
            continue
        for key, cl in comps.items():
            if any(c["class"] == so_name for c in cl):
                if _enrich_key(key, meta):
                    enriched += 1
                break
    # 同名互播：同 name 规则共享富字段（不同来源对同一 SDK 各持一条）
    by_name = {}
    for r in sdks.values():
        by_name.setdefault(r["name"], []).append(r)
    for group in by_name.values():
        rich = next((r for r in group if r.get("description")), None)
        if rich:
            for r in group:
                r["description"] = r.get("description") or rich.get("description", "")
                r["devTeam"] = r.get("devTeam") or rich.get("devTeam", "")
                r["sourceLink"] = r.get("sourceLink") or rich.get("sourceLink", "")

    # ── 5b. 样本审计增补（K1 六样本 927 未识别组件研判，2026-09-20；事实=组件前缀）──
    # 定性依据：官方 SDK 文档/行业知识；confidence 最高 medium（无正源 safeToBlock 标注）
    SAMPLE_AUDIT_ADDITIONS = [
        # (name, company, category, prefixes, confidence)
        ("Douyin Live Lite", "ByteDance", "social_or_pay", ["com.byted.live.lite"], "medium"),
        ("Alipay Mobile SDK", "Ant Group", "social_or_pay", ["com.alipay.mobile", "com.alipay.user.mobile", "com.alipay.android.phone"], "medium"),
        ("Ant mPaaS Container", "Ant Group", "infra", ["com.mpaas", "com.alibaba.ariver"], "medium"),
        ("Baidu Face Recognition", "Baidu", "security", ["com.baidu.idl.face", "com.baidu.oauth.sdkbqt"], "medium"),
        ("DCloud uni-app Container", "DCloud", "infra", ["io.dcloud"], "medium"),
        ("Meishu Ad", "Meishu", "ads", ["com.meishu.sdk"], "medium"),
        ("SmartDigi Ad", "SmartDigi", "ads", ["com.smartdigimkt"], "medium"),
        ("Ubix SSP", "Ubix", "ads", ["com.ubix.ssp", "com.ubix.wm"], "medium"),
        ("JY Ad", "JY", "ads", ["cn.jy.ad"], "low"),
        ("GalleryFinal", "finalteam", "infra", ["cn.finalteam.galleryfinal"], "medium"),
        ("Octopus Ad", "Octopus", "ads", ["com.octopus.ad"], "low"),
        ("Mercury Ad", "Mercury", "ads", ["com.mercury.sdk"], "low"),
        ("Hxad Ad", "Hxad", "ads", ["com.hxad.sdk"], "low"),
        ("Mcto SSP", "Mcto", "ads", ["com.mcto.sspsdk"], "low"),
        ("CJ Mobile Ad", "CJ Mobile", "ads", ["cj.mobile"], "low"),
        ("Douyin Pay", "ByteDance", "social_or_pay", ["com.ss.android.dypay"], "medium"),
        ("Tencent Face Verification (Huiyan)", "Tencent", "security", ["com.tencent.cloud.huiyansdk", "com.tencent.cloud.huiyansdkocr"], "medium"),
        ("Tencent Cloud TRTC/LiteAV", "Tencent", "infra", ["com.tencent.liteav", "com.tencent.rtmp", "com.tencent.qcloud.ugckit"], "medium"),
        ("Tencent RMonitor APM", "Tencent", "quality", ["com.tencent.rmonitor"], "medium"),
        ("Google Play Billing", "Google", "social_or_pay", ["com.android.billingclient"], "high"),
        ("CCB NetPay", "China Construction Bank", "social_or_pay", ["com.ccb.ccbnetpay"], "medium"),
        ("Zyh Metro SDK", "Gioneco", "infra", ["org.gioneco.zyhmetrosdk"], "low"),
        # ── K5 联网研判（2026-09-20，证据=隐私政策清单/官方接入文档/GitHub）──
        ("PTG Ad", "PTG", "ads", ["com.ptg.ptgapi"], "medium"),
        ("Qingyun Ad", "Qingyun", "ads", ["com.qy.sdk"], "low"),
        ("Zongliang Ad", "Zongliang", "ads", ["com.zongliang.sdk"], "medium"),
        ("Tencent SHLogin", "Tencent", "social_or_pay", ["com.shlogin.sdk"], "medium"),
        # 酷安样本发现（2026-09-20）
        ("NetEase Yidun QuickLogin", "NetEase", "social_or_pay", ["com.netease.nis.quicklogin"], "medium"),
        ("Volcengine OneKit", "ByteDance", "infra", ["com.volcengine.onekit"], "medium"),
        ("Tencent QCloud LogUtils", "Tencent", "quality", ["com.tencent.qcloud.logutils"], "low"),
        # ── K6 应用宝批量样本（2026-09-20，Range 审计 8 应用 6834 组件）──
        ("FinClip Mini-App Container", "Finogeeks", "infra", ["com.finogeeks"], "medium"),
        ("Douyin MiniApp Host", "ByteDance", "infra", ["com.tt.miniapphost", "com.tt.miniapp"], "medium"),
        ("Feisuo Ad", "Lianyan (Shanghai)", "ads", ["com.zm.adxsdk"], "medium"),
        ("Aliyun Short Video Editor", "Alibaba", "infra", ["com.aliyun.svideo"], "medium"),
        ("Alibaba ExtHub", "Alibaba", "analytics", ["com.alibaba.exthub"], "low"),
        ("TTC Pay OCR", "TTC", "social_or_pay", ["com.android.ttcjpaysdk"], "low"),
        ("Taobao Interaction Channel", "Alibaba", "infra", ["com.taobao.process.interaction"], "low"),
        ("Embedded Chromium WebView", "Chromium", "infra", ["org.chromium.content"], "low"),
        ("Unity WebGL Host", "Unity", "infra", ["com.u3d"], "low"),
        ("AIMi Push", "AIMi", "push", ["com.aimi.android"], "low"),
        # ── 手机批 352 应用（2026-09-21，跨家分发≥3 实证 + 联网定性）──
        ("Sobot Chat SDK", "Sobot", "infra", ["com.sobot.chat"], "medium"),
        ("NetEase Qiyukf", "NetEase", "infra", ["com.qiyukf"], "medium"),
        ("Geetest OneLogin", "Geetest", "social_or_pay", ["com.geetest.onelogin"], "medium"),
        ("JD Pay SDK", "JD", "social_or_pay", ["com.jdpaysdk"], "medium"),
        ("Ali Account SDK", "Alibaba", "social_or_pay", ["com.ali.user.mobile"], "medium"),
        ("Alipay Face ZIM", "Ant Group", "security", ["com.alipay.face"], "medium"),
        ("Aliyun RealIdentity", "Alibaba", "security", ["com.alibaba.security.realidentity"], "medium"),
        ("Aliyun DTF Face Verify", "Alibaba", "security", ["com.dtf.face", "com.dtf.wish"], "medium"),
        ("Alipay MSP Checkout", "Ant Group", "social_or_pay", ["com.alipay.android.msp"], "medium"),
        ("Alipay Push SDK", "Ant Group", "push", ["com.alipay.pushsdk"], "medium"),
        ("Bigo Ads", "Bigo", "ads", ["sg.bigo.ads"], "medium"),
        ("UnionPay SDK", "China UnionPay", "social_or_pay", ["com.unionpay"], "high"),
        ("Stripe Payments", "Stripe", "social_or_pay", ["com.stripe.android"], "high"),
        ("CloudWalk Face", "CloudWalk", "security", ["cn.cloudwalk"], "medium"),
        ("UniWebView", "onevcat", "infra", ["com.onevcat.uniwebview"], "medium"),
        ("ImageCropper (CanHub)", "CanHub", "infra", ["com.canhub.cropper"], "medium"),
        ("Flutter File Picker", "crazecoder", "infra", ["com.crazecoder.openfile"], "medium"),
        ("Flutter ImagePicker", "Flutter", "infra", ["com.imagepicker"], "low"),
        ("DMCBIG MediaPicker", "dmcbig", "infra", ["com.dmcbig.mediapicker"], "medium"),
        ("Expo Framework", "Expo", "infra", ["expo.modules"], "high"),
        ("Flutter Firebase Plugins", "Flutter", "infra", ["io.flutter.plugins"], "low"),
        ("YubiKit", "Yubico", "security", ["com.yubico.yubikit"], "medium"),
        ("libxposed Service API", "libxposed", "infra", ["io.github.libxposed.service"], "medium"),
        ("MobTech SDK", "MobTech", "social_or_pay", ["cn.fly", "com.mob.tools"], "high"),
        ("Lenovo LSF Pass", "Lenovo", "social_or_pay", ["com.lenovo.lsf"], "medium"),
        ("SCCA Auth SDK", "SCCA", "security", ["cn.com.scca.sccaauthsdk"], "low"),
        ("EFS MemLeak Monitor", "EFS", "quality", ["com.efs.sdk"], "low"),
        ("VirtualApp Framework", "VirtualApp", "infra", ["com.lody.virtual"], "medium"),
        ("VirtualAPK Framework", "Didi", "infra", ["com.didi.virtualapk"], "medium"),
        ("GeckoView", "Mozilla", "infra", ["org.mozilla.gecko"], "medium"),
        ("MagAppX Forum", "Duohuo", "infra", ["net.duohuo.magappx"], "low"),
        ("Meituan MtWebKit", "Meituan", "infra", ["com.meituan.mtwebkit"], "low"),
        ("Unity Mobile Notifications", "Unity", "infra", ["com.unity.androidnotifications"], "medium"),
        ("Agora RTC2", "Agora", "infra", ["io.agora.rtc2"], "medium"),
        ("Ali TBAuth", "Alibaba", "social_or_pay", ["com.ali.user.open"], "low"),
        # ── G1 网迈 lywm 补录（2026-10-21，OOPZ v1.1.10 manifest 实证 5 组件 + 联网定性
        #    旺脉科技 adwangmai.com，开屏/激励视频/插屏/原生信息流；authorities 特征
        #    lywmLifecycleProvider/lywmfileprovider，反作弊 so liblywmAliAgainstId.so）──
        ("Wangmai Ad (lywm)", "Wangmai Technology", "ads", ["com.wangmai.insightvision"], "medium"),
    ]
    n_audit = 0
    for name, company, cat, prefs, conf in SAMPLE_AUDIT_ADDITIONS:
        put(f"audit:{name}", name, company, cat, prefs, False, "",
            ["sample-audit-202609(facts)"], conf, [])
        n_audit += 1

    # 既有规则前缀并入（K3 归类确认项：族匹配 + 人工定性）
    # K5b：缺失描述补全（2026-09-20，口径=官方文档中性描述；联网+知识研判，来源标注）
    NAME_DESCRIPTIONS = {'Alipay Mobile SDK': '蚂蚁集团支付宝移动支付 SDK，提供收单、支付回调与钱包能力。', 'Ant mPaaS Container': '蚂蚁集团 mPaaS 移动开发平台容器（H5/小程序容器 mriver 与 ariver 引擎）。', 'Aurora Push': '和极光推送（JPush），提供 App 消息推送通道与厂商通道整合。', 'AutoNavi / Amap': '高德地图开放平台定位/地图 SDK。', 'Baidu Face Recognition': '百度智能云人脸识别离线 SDK（采集、活体、比对）。', 'CCB NetPay': '中国建设银行手机支付 SDK（龙卡支付组件）。', 'CJ Mobile Ad': 'CJ Mobile 广告联盟组件（样本审计收录，归属待厂商确认）。', 'DCloud uni-app Container': 'DCloud uni-app 跨端框架运行时与原生插件桥。', 'Douyin Live Lite': '抖音开放平台直播分享轻量组件（字节跳动）。', 'Douyin Pay': '抖音支付组件（字节跳动）。', 'GalleryFinal': '开源相册/拍照选择库 GalleryFinal（finalteam）。', 'Getui SDK': '个推消息推送 SDK（合并主流厂商通道）。', 'Google Play Billing': 'Google Play 应用内购买结算库。', 'HMS Core Ads SDK': '华为移动服务广告标识与广告能力组件（OAID 等）。', 'Honor Ad Alliance': '荣耀广告联盟（HiAds）组件。', 'Hxad Ad': 'Hxad 广告联盟组件（样本审计收录，归属待厂商确认）。', 'JD CPS Alliance SDK': '京东开普勒 CPS 分销联盟组件（京东商品导购）。', 'JY Ad': 'JY 广告组件（样本审计收录，低置信）。', 'Kuaishou Advertising Alliance': '快手磁力引擎广告联盟（开屏/信息流变现）。', 'Mcto SSP': 'Mcto SSP 广告供给方组件（样本审计收录，低置信）。', 'Meishu Ad': '美数广告平台 SDK（程序化广告）。', 'Mercury Ad': 'Mercury 广告组件（样本审计收录，低置信）。', 'Octopus Ad': '章鱼广告组件（样本审计收录，低置信）。', 'Oppo Advertising Alliance': 'OPPO 互联网广告组件（广告标识与联盟）。', 'PTG Ad': 'PTG 广告 SDK（支持 TopOn 聚合适配，含下载服务）。', 'Pangle': '字节跳动穿山甲 GroMore/Pangle 国际版广告组件。', 'Pangolin Advertising SDK': '字节跳动穿山甲广告 SDK（开屏/激励视频/信息流；含内部渲染子包 com.byazt）。', 'Qingyun Ad': '青云广告 SDK（qyzss.com，低置信）。', 'Qumeng 趣盟': '趣盟聚合广告组件（Fuck.AD 提取事实收录）。', 'Sigmob': 'Sigmob 移动广告聚合平台 SDK（创智汇聚）。', 'SmartDigi Ad': 'SmartDigi（智玛）程序化广告 SDK。', 'Tencent Bugly': '腾讯 Bugly 崩溃分析与异常上报 SDK。', 'Tencent Cloud TRTC/LiteAV': '腾讯云实时音视频 TRTC / 短视频 LiteAV 组件。', 'Tencent Face Verification (Huiyan)': '腾讯云慧眼人脸核身 SDK（实名认证）。', 'Tencent RMonitor APM': '腾讯 RMonitor 性能监控组件。', 'Tencent SHLogin': '腾讯一键登录/本机号码认证组件。', 'Tencent Tinker hot update': '腾讯 Tinker 热修复框架（补丁下发与加载）。', 'TopOn SDK': 'TopOn（塔酷）广告聚合中介平台 SDK，统一调度多家广告网络。', 'Ubix SSP': 'Ubix 广告供给方平台 SDK。', 'Vivo Advertising Alliance': 'vivo 广告联盟组件。', 'Windmill 风车': 'WindMill 风车聚合广告组件（Fuck.AD 提取事实收录）。', 'Xiaomi Mobile Ads Alliance (Mimo Ad SDK)': '小米米盟广告 SDK。', 'Zongliang Ad': '纵量广告 SDK（开屏广告，docs.adprod.cn）。', 'HMS Core': '华为移动服务核心库（推送/账号/广告标识等基础能力）。'}

    for _r in sdks.values():
        d = NAME_DESCRIPTIONS.get(_r["name"])
        if d and not _r.get("description"):
            _r["description"] = d

    # G1（2026-10-21）：网迈 lywm 中文描述——authorities/so 特征一并留档（authority 锚点触发器启动时可直接取用）
    _wm = next((x for x in sdks.values() if x["name"] == "Wangmai Ad (lywm)"), None)
    if _wm is not None and not _wm.get("description"):
        _wm["description"] = (
            "旺脉（网迈）广告 SDK：开屏/激励视频/插屏/原生信息流广告组件（公司主体 adwangmai.com）。"
            "组件前缀 com.wangmai.insightvision；authorities 特征 lywmLifecycleProvider/lywmfileprovider"
            "（宿主包名前缀拼接）；反作弊 so liblywmAliAgainstId.so。"
        )

    # G2③（2026-10-21）：byted.live.lite 组件归位——LCR Pangle SDK 规则错挂抖音直播 lite 的
    # ServerManager provider（byted.live.lite 前缀应归 Douyin Live Lite 实体），组件级重定向
    _pk = next((k for k, v in sdks.items() if v["name"] == "Pangle SDK"), None)
    _dk = next((k for k, v in sdks.items() if v["name"] == "Douyin Live Lite"), None)
    if _pk is not None and _dk is not None:
        _stay = [c for c in comps[_pk] if not c["class"].startswith("com.byted.live.lite")]
        _move = [c for c in comps[_pk] if c["class"].startswith("com.byted.live.lite")]
        if _move:
            comps[_pk] = _stay
            comps[_dk].extend(_move)
            print(f"G2c: moved {len(_move)} byted.live.lite providers Pangle->DouyinLiveLite")

    PREFIX_MERGES = {
        # byazt = 穿山甲内部渲染子包（多款 app 隐私政策将 com.byazt 与穿山甲并列申报）——并入而非新建
        "Pangolin Advertising SDK": ["com.byazt"],
        # 批GG-G3（2026-10-21）：巡检发现 PTG 第二命名空间 com.ptg.adsdk（KOOK+OOPZ 两样本实证）
        "PTG Ad": ["com.ptg.adsdk"],
        # 批H 回滚：com.unity3d.player 是 Unity 引擎命名空间（批K 误并入 Ads，致无广告 Unity 游戏误报）
        "OPPO Push": ["com.heytap.msp.push"],
        "Facebook": ["com.facebook.others"],
        "BeiZi SDK": ["com.beizi.fusion"],
        # 手机批前缀并入（2026-09-21）
        "Ant mPaaS Container": ["com.alibaba.triver"],
        "Ali TBAuth": ["com.taobao.login4android", "com.taobao.uc.service"],
        "Alipay Mobile SDK": ["com.alipay.android.msp.ui"],
        "Braze (formerly Appboy)": ["com.braze"],
        "Facebook Share": ["com.facebook.unity", "com.facebook.smartcapture"],
        "Jetpack Car": ["androidx.car.app"],
        "MiPush": ["com.xiaomi.push.service"],
        "Vivo Advertising Alliance": ["com.vivo.adloadsdk", "com.vivo.ic.dm"],
        "Honor Ad Alliance": ["com.hihonor.id.router"],
    }
    for rname, extra in PREFIX_MERGES.items():
        r = next((x for x in sdks.values() if x["name"] == rname), None)
        if r is not None:
            r["packPrefixes"] = sorted(set(r["packPrefixes"]) | {e + "." for e in extra})

    # 批K K2：组件终排序——glob 序已排序，此处再按 (type, class) 稳定终序，跨平台字节一致
    for key in comps:
        comps[key].sort(key=lambda c: (c["type"], c["class"]))

    out = {
        "aliases": ALIAS_MERGES,
        "schemaVersion": 1,
        "generatedAt": freeze_at,
        "generator": generator,
        "license": "Apache-2.0 (sources: blocker-general-rules, LibChecker-Rules; facts: Fuck.AD dex, oF2pks index)",
        "stats": {"sdks": len(sdks), "blocker": n_blocker, "fuckad": n_fuckad, "sampleAudit": n_audit,
                  "lcrComponents": comp_count, "lcrSo": so_count, "of2pks": n_of2pks},
        "sdks": [],
    }
    for key, r in sdks.items():
        r["components"] = comps[key]
        out["sdks"].append(r)
    return out, enriched


def main():
    ap = argparse.ArgumentParser(description="Prunoid-Rules snapshot builder（批K 归一版）")
    ap.add_argument("--lcr-repo", required=True, help="LibChecker-Rules 本地 clone 根目录（pin 见 upstream_pins.json）")
    ap.add_argument("--blocker-json", required=True, help="blocker-general-rules rules/en/general.json 路径")
    ap.add_argument("--of2pks-txt", required=True, help="oF2pks trackers448NEW.txt 路径（上游固定 commit，勿捆绑入库）")
    ap.add_argument("--out", required=True, help="输出 snapshot.json 路径")
    ap.add_argument("--freeze-at", required=True,
                    help="generatedAt 固定值（ISO 时间）——发布产物必填，保证 byte 可复现")
    ap.add_argument("--generator", default="prunoid-rules/build_snapshot.py",
                    help="generator 字段标识（默认中性仓内路径）")
    a = ap.parse_args()
    if not a.freeze_at:
        raise SystemExit("--freeze-at required（发布产物必须固定时间戳）")
    # 校验 freeze-at 可解析，防手滑
    datetime.fromisoformat(a.freeze_at)

    out, enriched = build(a.lcr_repo, a.blocker_json, a.of2pks_txt, a.freeze_at, a.generator)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    s = out["stats"]
    print(f"sdks={s['sdks']} blocker={s['blocker']} fuckad={s['fuckad']} sampleAudit={s['sampleAudit']} "
          f"lcrComp={s['lcrComponents']} lcrSo={s['lcrSo']} of2pks={s['of2pks']} enriched={enriched}")
    print(f"size={os.path.getsize(a.out)/1024:.0f}KB -> {a.out}")


if __name__ == "__main__":
    main()
