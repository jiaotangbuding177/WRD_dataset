"""Offline privacy transformation for a new WRD public derivative.

Never rewrites the original bundle. Salt and reversible raw-value mappings are
kept only in the caller-supplied local restricted directory. Pattern coverage is
explicitly limited; this module does not certify complete anonymization.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import threading
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


VERSION = "wrd-public-privacy-v1"


def _key(value: str) -> str:
    return re.sub(r"[\s_.-]+", "", str(value)).lower()


SECRET_KEYS = {
    "apikey", "authorization", "password", "passwd", "accesstoken",
    "refreshtoken", "gatewaytoken", "clientsecret", "privatekey", "secretkey",
    "awssecretaccesskey", "awsaccesskeyid", "sessionid", "sessionkey",
    "csrftoken", "xsrftoken", "cookie", "cookies", "setcookie",
    "browserstorage", "localstorage", "sessionstorage", "auth",
}
PERSON_KEYS = {
    "姓名", "真实姓名", "联系人", "联系人姓名", "员工姓名", "候选人姓名",
    "求职者姓名", "患者姓名", "收件人", "户名", "fullname", "realname",
    "personname", "contactname", "candidatename", "employeename",
    "patientname", "applicantname", "customername", "recipientname",
}
PHONE_KEYS = {"phone", "phonenumber", "telephone", "mobile", "mobilenumber", "联系电话", "联系方式", "手机号", "手机号码", "电话"}
CONTACT_HANDLE_KEYS = {"wechat", "weixin", "微信", "微信号", "qq", "qq号", "telegram", "个人微信"}
EMAIL_KEYS = {"email", "emailaddress", "邮箱", "电子邮箱", "电子邮件"}
ID_KEYS = {"身份证", "身份证号", "身份证号码", "idnumber", "identitynumber", "nationalid", "passportnumber", "护照号", "社保号", "socialsecuritynumber"}
BANK_KEYS = {"银行卡", "银行卡号", "银行账号", "银行账户", "bankaccount", "bankaccountnumber", "cardnumber", "iban", "routingnumber"}
ADDRESS_KEYS = {"家庭住址", "个人住址", "联系地址", "通讯地址", "邮寄地址", "homeaddress", "residentialaddress", "mailingaddress", "contactaddress"}
PERSON_ATTRIBUTE_KEYS = {"出生日期", "出生年月", "dateofbirth", "dob", "民族", "宗教", "religion", "ethnicity", "婚姻状况", "maritalstatus", "婚育状况", "婚育", "生育情况", "政治面貌", "政治身份", "politicalaffiliation", "politicalstatus", "partymembership", "性取向", "sexualorientation", "健康状况", "疾病史", "既往史", "残疾情况", "disability", "孕产情况", "pregnancy", "工会身份", "tradeunionmembership"}
PRIVATE_PAY_KEYS = {"当前薪资", "目前薪资", "期望薪资", "个人收入", "年收入", "currentsalary", "expectedsalary", "personalincome", "annualincome", "工资流水"}
MEDICAL_KEYS = {"诊断结果", "既往病史", "病历号", "患者病史", "体检结果", "medicalrecordnumber", "patienthistory", "diagnosisresult"}
LOCAL_METADATA_KEYS = {"sourcepath", "hostpath", "originalpath", "consumer", "profile", "credentials", "inputroot", "workspaceroot"}
CONTACT_CONTEXT_KEYS = PHONE_KEYS | CONTACT_HANDLE_KEYS | EMAIL_KEYS | ID_KEYS | ADDRESS_KEYS | PERSON_ATTRIBUTE_KEYS | PRIVATE_PAY_KEYS | MEDICAL_KEYS

EMAIL_RE = re.compile(r"(?<![\w.+-])[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,24}(?![\w.-])")
PHONE_RE = re.compile(r"(?<![\dA-Za-z])(?:\+?86[- ]?)?1[3-9]\d{9}(?![\dA-Za-z])")
ID_RE = re.compile(r"(?<![\dA-Za-z])[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?![\dA-Za-z])")
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)
WINDOWS_USER_RE = re.compile(r"(?i)\b([A-Z]:[\\/]+Users[\\/]+)([^\\/\s\"'<>:]+)")
ABS_LOCAL_RE = re.compile(r"(?i)^(?:[CDE]:[\\/]|file:///[CDE]:[\\/])")
SOURCE_ID_RE = re.compile(r"\bconv_[a-f0-9]{12}\b")

PERSON_LABEL_RE = re.compile(r"((?:姓名|真实姓名|联系人(?:姓名)?|员工姓名|候选人姓名|求职者姓名|患者姓名|户名|收件人)\s*[:：=]\s*)([\u4e00-\u9fff]{2,4})(?=[\s,，;；。\"'|/]|$)")
PHONE_LABEL_RE = re.compile(r"((?:联系电话|手机号码?|手机号|电话|tel(?:ephone)?|mobile)\s*[:：=]\s*)(\+?[\d][\d ()-]{6,24}\d)", re.I)
CONTACT_HANDLE_LABEL_RE = re.compile(r"((?:微信(?:号)?|weixin|wechat|QQ(?:号)?|telegram)\s*[:：=]\s*)([A-Za-z0-9_@+.-]{4,64})", re.I)
BANK_LABEL_RE = re.compile(r"((?:银行卡号?|银行账号|银行账户|bank[_ -]?account(?:[_ -]?number)?|IBAN)\s*[:：=]\s*)([A-Za-z]{0,2}[\d][A-Za-z\d -]{5,32})", re.I)
ADDRESS_LABEL_RE = re.compile(r"((?:家庭住址|个人住址|联系地址|通讯地址|邮寄地址|home[_ -]?address|residential[_ -]?address)\s*[:：=]\s*)([^\r\n;；\"']{3,160})", re.I)
PRIVATE_VALUE_LABEL_RE = re.compile(r"((?:当前薪资|目前薪资|期望薪资|个人收入|年收入|出生日期|出生年月|民族|宗教|婚姻状况|婚育状况|婚育|生育情况|政治面貌|政治身份|性取向|健康状况|疾病史|既往史|残疾情况|孕产情况|工会身份|诊断结果|既往病史|病历号|体检结果|患者病史)\s*[:：=]\s*)([^\r\n;；\"']{1,160})")

SECRET_TOKEN_RE = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AIza[A-Za-z0-9_-]{30,}|AKIA[A-Z0-9]{16})\b")
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
PEM_RE = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
AUTH_RE = re.compile(r"(?i)((?:Bearer|Basic)\s+)[A-Za-z0-9_.~+/=-]{8,}")
ASSIGN_SECRET_RE = re.compile(r"(?i)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd|authorization|session[_-]?id|csrf[_-]?token)[\"']?\s*[:=]\s*)([\"']?)([^\s\r\n,;\"']{1,})([\"']?)")
COOKIE_HEADER_RE = re.compile(r"(?im)((?:set-cookie|cookie)\s*[:=]\s*)([^\r\n\"']+)")
COOKIE_QUOTED_ASSIGN_RE = re.compile(r"(?i)((?:document\.cookie|cookie|cookies|localStorage|sessionStorage)\s*[:=]\s*)([\"'])([^\r\n]*?)(\2)")
COOKIE_ASSIGN_RE = re.compile(r"(?i)((?:qcc_did|UM_distinctid|UM_distinct|JSESSIONID|PHPSESSID|SESSIONID|session_id|csrftoken|_csrf|auth_token|access_token|refresh_token|__Secure-[A-Za-z0-9_-]+)\s*=\s*)([^\s;\r\n\"']+)")
COOKIE_JSON_RE = re.compile(r"(?i)([\"'](?:cookie|cookies|set-cookie|sessionid|browser_storage|localStorage|sessionStorage)[\"']\s*:\s*)([\"'])([^\r\n]*?)(\2)")

SENSITIVE_QUERY_KEYS = {"token", "accesstoken", "refreshtoken", "apikey", "secret", "clientsecret", "sig", "signature", "authorization", "password", "sessionid", "sessionkey", "auth", "code", "xamzsignature", "xamzcredential", "xamzsecuritytoken", "xgoogsignature", "xgoogcredential"}
RESERVED_DOMAINS = {"example.com", "example.org", "example.net", "example.invalid", "localhost", "test.invalid"}
EXACT_SAFE_VALUES = {"<redacted_credential>", "<redacted_credential_location>", "<redacted>", "[redacted]", "[隐藏]", "***", "***hex***", "<hidden>", "<placeholder>", "placeholder", "未提供", "待补", "待补充", "未知", "匿名", "需补充"}
TYPED_ALIAS_RE = re.compile(r"(?:PERSON|ADDRESS|PERSON_ATTRIBUTE|PRIVATE_PAY|MEDICAL|LOCAL_PATH|SOURCE|LOCAL_USER|CONTACT_HANDLE)_[a-f0-9]{12}\Z")
ENV_REFERENCE_RE = re.compile(r"(?:\$\{[A-Za-z_][A-Za-z0-9_]*\}|\$env:[A-Za-z_][A-Za-z0-9_]*|\$[A-Za-z_][A-Za-z0-9_]*|os\.environ\[[\"'][A-Za-z_][A-Za-z0-9_]*[\"']\]|os\.(?:getenv|environ\.get)\([\"'][A-Za-z_][A-Za-z0-9_]*[\"']\)|process\.env\.[A-Za-z_][A-Za-z0-9_]*|process\.env\[[\"'][A-Za-z_][A-Za-z0-9_]*[\"']\])\Z")
MEDICAL_RECORD_RE = re.compile(r"(?:患者(?:姓名|身份证|病史)|病历号|诊断结果|既往病史|体检结果)\s*[:：=]\s*[^\s;；\r\n]{2,}")
UNTERMINATED_KEY_RE = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
MEDIA_PAYLOAD_RE = re.compile(r"data:(?:image/|application/pdf|audio/|video/)", re.I)
FILE_TOKEN_RE = re.compile(r"[^\s\"'<>\\/]{1,180}\.(?:pdf|docx?|txt|xlsx?)(?![A-Za-z0-9])", re.I)
CHINESE_RUN_RE = re.compile(r"[\u4e00-\u9fff]{2,4}")
RESUME_HINT_RE = re.compile(r"简历|求职|应聘|resume|candidate|curriculum|CV\b", re.I)
RESUME_NAME_LINE_RE = re.compile(r"(?m)^\s*([\u4e00-\u9fff]{2,4})\s*(?:[|｜]|(?=\r?$)|(?=(?:男|女|\d{2}岁|期望薪资|求职)))")
CHINESE_SURNAMES = set("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄穆萧尹姚邵汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯昝管卢莫经房裘缪解应宗丁宣邓郁单杭洪包诸左石崔吉龚程嵇邢裴陆荣翁荀羊甄曲封芮储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲邰从鄂索咸籍赖卓蔺屠蒙池乔阴胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍却璩桑桂濮牛寿通边扈燕冀郏浦尚农温别庄晏柴瞿阎充慕连茹习艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘匡国文寇广禄阙东欧利师巩聂晁勾敖融冷訾辛阚那简饶空曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公晋楚闫岳帅缑亢况郈有琴归海舌梁丘左丘商牟佘佴伯赏墨哈谯笪年爱阳佟言福")
COMPOUND_SURNAMES = {"欧阳", "司马", "上官", "诸葛", "东方", "夏侯", "皇甫", "尉迟", "公孙", "慕容", "司徒", "司空", "令狐", "长孙", "宇文", "轩辕"}
NAME_STOPWORDS = {"简历", "个人简历", "候选人", "联系人", "工作经历", "教育经历", "求职意向", "基本信息", "个人信息", "联系电话", "联系方式", "手机号码", "员工姓名", "应聘岗位", "任职要求", "岗位要求", "高级工程", "工程师", "姓名", "姓名字段", "姓名示例", "求职", "资料", "附件", "材料", "文件", "公司", "岗位", "职位", "人才", "项目", "目录", "说明", "个人", "应聘", "员工", "示例", "参考", "内容"}
BIOGRAPHY_GROUP_PATTERNS = (
    re.compile(r"教育经历|毕业院校|毕业学校|毕业时间|学历|学位|本科|硕士|博士"),
    re.compile(r"工作经历|任职经历|任职时间|历任|就职|在职|工作年限|工作经验"),
    re.compile(r"出生日期|出生年月|年龄|婚育|婚姻|民族|政治面貌|宗教|期望薪资|当前薪资|个人收入"),
)
PROTECTED_PERSONAL_VALUE_RE = re.compile(r"(?:政治面貌|政治身份|民族|宗教|婚育状况|婚姻状况|健康状况|性取向|残疾情况)\s*[:：=]\s*\S+|中共(?:预备)?党员|已婚已育|未婚未育|离异|信仰(?:基督|伊斯兰|佛教)")
EDUCATION_KEYS = {"education", "educationhistory", "educations", "university", "college", "school", "degree", "学历", "学位", "学校", "毕业院校", "教育经历"}
EMPLOYMENT_KEYS = {"workhistory", "workexperience", "employment", "career", "positions", "employer", "工作经历", "任职经历", "工作年限", "工作经验", "任职", "职业经历"}
PERSON_CONTAINER_KEYS = {"person", "candidate", "patient", "employee", "applicant", "personalinfo", "personalinformation", "个人", "候选人", "员工", "患者", "个人信息"}


def _plausible_chinese_name(value: str) -> bool:
    return bool(re.fullmatch(r"[\u4e00-\u9fff]{2,4}", value)) and value not in NAME_STOPWORDS and not any(word in value for word in ("简历", "候选", "岗位", "姓名", "要求", "工程", "工作")) and (value[0] in CHINESE_SURNAMES or value[:2] in COMPOUND_SURNAMES)


def _name_candidates(text: str) -> set[str]:
    result = {m.group(2) for m in PERSON_LABEL_RE.finditer(text) if _plausible_chinese_name(m.group(2))}
    for match in FILE_TOKEN_RE.finditer(text):
        token = match.group(0)
        context = text[max(0, match.start() - 100): min(len(text), match.end() + 80)]
        if RESUME_HINT_RE.search(context):
            stem = token.rsplit(".", 1)[0]
            for part in re.split(r"[_\-（）()\[\]【】+.,，]", stem):
                if _plausible_chinese_name(part):
                    result.add(part)
            if stem.endswith("简历") and _plausible_chinese_name(stem[:-2]):
                result.add(stem[:-2])
            if stem.startswith("简历") and _plausible_chinese_name(stem[2:]):
                result.add(stem[2:])
    for match in RESUME_NAME_LINE_RE.finditer(text):
        context = text[max(0, match.start() - 120): min(len(text), match.end() + 250)]
        if _plausible_chinese_name(match.group(1)) and re.search(r"简历|性别|手机|邮箱|求职|年龄|工作经历|期望薪资|出生", context):
            result.add(match.group(1))
    return result


class Sanitizer:
    def __init__(self, restricted_dir: str | Path, pseudonymize_source_ids: bool = False):
        self.restricted_dir = Path(restricted_dir).absolute()
        self.restricted_dir.mkdir(parents=True, exist_ok=True)
        salt_path = self.restricted_dir / "privacy_hmac_salt.bin"
        try:
            with salt_path.open("xb") as handle:
                handle.write(secrets.token_bytes(32))
        except FileExistsError:
            pass
        self._salt = salt_path.read_bytes()
        if len(self._salt) != 32:
            raise ValueError("invalid private HMAC salt length")
        self.pseudonymize_source_ids = pseudonymize_source_ids
        self._lock = threading.RLock()
        self._mapping: dict[str, dict] = {}
        self._safe_values: set[str] = set()
        self._names: dict[str, str] = {}
        self._name_re = None
        self.discovery_frozen = False
        self.discovery_calls = 0
        self.counts = Counter()
        self.row_counts = Counter()
        mapping_path = self.restricted_dir / "privacy_private_mapping.json"
        if mapping_path.exists():
            saved = json.loads(mapping_path.read_text(encoding="utf-8"))
            for item in saved.get("entries", []):
                self._mapping[item["mapping_key"]] = item
                self._safe_values.add(item["replacement"])
                if item["kind"] == "PERSON":
                    self._names[item["raw_value"]] = item["replacement"]

    def _safe(self, value) -> bool:
        if not isinstance(value, (str, int)) or isinstance(value, bool):
            return False
        text = str(value)
        return text in self._safe_values or text.strip().lower() in EXACT_SAFE_VALUES or bool(TYPED_ALIAS_RE.fullmatch(text.strip())) or bool(ENV_REFERENCE_RE.fullmatch(text.strip()))

    def _replace(self, kind: str, value, numeric: bool = False, count: bool = True):
        raw = str(value)
        if not raw or self._safe(raw):
            return value
        mapping_key = kind + "\0" + raw
        with self._lock:
            if mapping_key not in self._mapping:
                digest = hmac.new(self._salt, mapping_key.encode("utf-8"), hashlib.sha256).hexdigest()
                if kind == "EMAIL":
                    replacement = "email_" + digest[:12] + "@example.invalid"
                elif kind in {"PHONE", "GOVERNMENT_ID", "BANK_ACCOUNT"}:
                    digits = str(int(digest, 16))
                    if kind == "PHONE":
                        replacement = "100" + digits[:8]
                    elif kind == "GOVERNMENT_ID":
                        replacement = "90000000000000" + digits[:4]
                    else:
                        width = max(8, min(24, sum(c.isdigit() for c in raw)))
                        replacement = "900000" + digits[:width - 6]
                else:
                    replacement = kind + "_" + digest[:12]
                self._mapping[mapping_key] = {"mapping_key": mapping_key, "kind": kind, "raw_value": raw, "replacement": replacement}
                self._safe_values.add(replacement)
            replacement = self._mapping[mapping_key]["replacement"]
            if count:
                self.counts[kind] += 1
        if numeric and isinstance(value, int) and not isinstance(value, bool) and replacement.isdigit():
            return int(replacement)
        return replacement

    def _secret(self, value):
        if not value or self._safe(value):
            return value
        self.counts["CREDENTIAL"] += 1
        return "<REDACTED_CREDENTIAL>"

    def _url(self, match: re.Match) -> str:
        text = match.group(0)
        try:
            parts = urlsplit(text)
            netloc = parts.netloc
            changed = False
            if "@" in netloc:
                netloc = netloc.rsplit("@", 1)[1]
                self.counts["URL_USERINFO"] += 1
                changed = True
            query = parse_qsl(parts.query, keep_blank_values=True)
            kept = [(k, v) for k, v in query if _key(k) not in SENSITIVE_QUERY_KEYS]
            if len(kept) != len(query):
                self.counts["URL_SECRET_QUERY"] += len(query) - len(kept)
                changed = True
            fragment = parts.fragment
            if "=" in fragment:
                fragment_pairs = parse_qsl(fragment, keep_blank_values=True)
                kept_fragment = [(k, v) for k, v in fragment_pairs if _key(k) not in SENSITIVE_QUERY_KEYS]
                if len(kept_fragment) != len(fragment_pairs):
                    fragment = urlencode(kept_fragment)
                    self.counts["URL_SECRET_FRAGMENT"] += len(fragment_pairs) - len(kept_fragment)
                    changed = True
            return urlunsplit((parts.scheme, netloc, parts.path, urlencode(kept) if len(kept) != len(query) else parts.query, fragment)) if changed else text
        except ValueError:
            self.counts["URL_PARSE_UNKNOWN"] += 1
            return text

    def clean_text(self, text: str) -> str:
        # Names discovered anywhere in the cohort must also change in earlier
        # paths, repeated observations, source code strings and current targets.
        if self._names:
            if self._name_re is None:
                self._name_re = re.compile("|".join(re.escape(x) for x in sorted(self._names, key=lambda x: (-len(x), x))))
            def replace_name(match):
                self.counts["DISCOVERED_PERSON_NAME"] += 1
                return self._names[match.group(0)]
            text = self._name_re.sub(replace_name, text)
        text = URL_RE.sub(self._url, text)
        for pattern, kind in ((PEM_RE, "PRIVATE_KEY"), (SECRET_TOKEN_RE, "CREDENTIAL_TOKEN"), (JWT_RE, "JWT")):
            def secret_sub(match, label=kind):
                self.counts[label] += 1
                return "<REDACTED_CREDENTIAL>"
            text = pattern.sub(secret_sub, text)
        text = AUTH_RE.sub(lambda m: m.group(1) + str(self._secret(m.group(0)[len(m.group(1)): ])), text)
        def assignment(match):
            return match.group(1) + match.group(2) + str(self._secret(match.group(3))) + match.group(4)
        text = ASSIGN_SECRET_RE.sub(assignment, text)
        def cookie_header(match):
            value = match.group(2)
            if self._safe(value):
                return match.group(0)
            self.counts["COOKIE_HEADER_OR_ASSIGNMENT"] += 1
            return match.group(1) + "<REDACTED_CREDENTIAL>"
        text = COOKIE_QUOTED_ASSIGN_RE.sub(lambda m: m.group(1) + m.group(2) + str(self._secret(m.group(3))) + m.group(4), text)
        text = COOKIE_HEADER_RE.sub(cookie_header, text)
        text = COOKIE_ASSIGN_RE.sub(lambda m: m.group(1) + str(self._secret(m.group(2))), text)
        text = COOKIE_JSON_RE.sub(lambda m: m.group(1) + m.group(2) + str(self._secret(m.group(3))) + m.group(4), text)
        def email(match):
            value = match.group(0)
            domain = value.rsplit("@", 1)[1].lower()
            return value if domain in RESERVED_DOMAINS or domain.endswith(".invalid") else str(self._replace("EMAIL", value))
        text = EMAIL_RE.sub(email, text)
        text = PHONE_RE.sub(lambda m: str(self._replace("PHONE", m.group(0))), text)
        text = ID_RE.sub(lambda m: str(self._replace("GOVERNMENT_ID", m.group(0))), text)
        for pattern, kind in ((PERSON_LABEL_RE, "PERSON"), (PHONE_LABEL_RE, "PHONE"), (CONTACT_HANDLE_LABEL_RE, "CONTACT_HANDLE"), (BANK_LABEL_RE, "BANK_ACCOUNT"), (ADDRESS_LABEL_RE, "ADDRESS"), (PRIVATE_VALUE_LABEL_RE, "PERSON_ATTRIBUTE")):
            text = pattern.sub(lambda m, label=kind: m.group(1) + str(self._replace(label, m.group(2))), text)
        text = WINDOWS_USER_RE.sub(lambda m: m.group(1) + str(self._replace("LOCAL_USER", m.group(2))), text)
        if self.pseudonymize_source_ids:
            text = SOURCE_ID_RE.sub(lambda m: str(self._replace("SOURCE", m.group(0))), text)
        return text

    def discover(self, value) -> dict:
        if self.discovery_frozen:
            return {"discovery_frozen": True, "person_names": len(self._names)}
        self.discovery_calls += 1
        self._discover_walk(value, ())
        return {"discovery_frozen": False, "person_names": len(self._names)}

    def _remember_name(self, value):
        if not isinstance(value, str) or self._safe(value) or not value.strip():
            return
        if len(value) <= 80:
            if value not in self._names:
                self._names[value] = str(self._replace("PERSON", value, count=False))
                self._name_re = None

    def _discover_walk(self, value, path):
        if isinstance(value, dict):
            contact_object = bool({_key(k) for k in value} & (CONTACT_CONTEXT_KEYS | EDUCATION_KEYS | EMPLOYMENT_KEYS))
            for key, item in value.items():
                if not path and key == "tools":
                    continue
                if _key(key) in PERSON_KEYS or (_key(key) == "name" and contact_object):
                    self._remember_name(item)
                self._discover_walk(item, path + (key,))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                self._discover_walk(item, path + (i,))
        elif isinstance(value, str):
            for name in _name_candidates(value):
                self._remember_name(name)
            if value.lstrip().startswith(("{", "[")):
                try:
                    parsed = json.loads(value)
                except (ValueError, RecursionError):
                    parsed = None
                if isinstance(parsed, (dict, list)):
                    self._discover_walk(parsed, path + ("embedded_json",))

    def freeze(self) -> dict:
        self.discovery_frozen = True
        self.save_private_mapping()
        return {"discovery_frozen": True, "person_names": len(self._names), "discovery_calls": self.discovery_calls}

    def clean_value(self, value):
        if not self.discovery_frozen:
            self.discover(value)
        return self._walk(value, ())

    def _walk(self, value, path: tuple):
        if isinstance(value, dict):
            result = {}
            keys = {_key(k) for k in value}
            contact_object = bool(keys & (CONTACT_CONTEXT_KEYS | EDUCATION_KEYS | EMPLOYMENT_KEYS))
            for key, item in value.items():
                norm = _key(key)
                if not path and key == "tools":
                    # The caller supplies the already verified public fixed-image
                    # schemas. Do not turn function names/schema examples into PII.
                    result[key] = item
                elif norm in SECRET_KEYS or re.fullmatch(r"(?:admin|user|db|database|smtp|email|service|login|root|test)?(?:apikey|password|passwd|accesstoken|refreshtoken|clientsecret|privatekey)", norm):
                    result[key] = self._secret(item)
                elif norm in PERSON_KEYS or (norm == "name" and contact_object):
                    result[key] = self._replace("PERSON", item) if isinstance(item, (str, int)) else self._walk(item, path + (key,))
                elif norm in PHONE_KEYS:
                    result[key] = self._replace("PHONE", item, numeric=True) if isinstance(item, (str, int)) else self._walk(item, path + (key,))
                elif norm in CONTACT_HANDLE_KEYS:
                    result[key] = self._replace("CONTACT_HANDLE", item) if isinstance(item, (str, int)) else self._walk(item, path + (key,))
                elif norm in EMAIL_KEYS:
                    result[key] = self.clean_text(item) if isinstance(item, str) else self._walk(item, path + (key,))
                elif norm in ID_KEYS:
                    result[key] = self._replace("GOVERNMENT_ID", item, numeric=True) if isinstance(item, (str, int)) else self._walk(item, path + (key,))
                elif norm in BANK_KEYS:
                    result[key] = self._replace("BANK_ACCOUNT", item, numeric=True) if isinstance(item, (str, int)) else self._walk(item, path + (key,))
                elif norm in ADDRESS_KEYS or (norm == "address" and contact_object):
                    result[key] = self._replace("ADDRESS", item) if isinstance(item, str) else self._walk(item, path + (key,))
                elif norm in PERSON_ATTRIBUTE_KEYS | PRIVATE_PAY_KEYS | MEDICAL_KEYS:
                    kind = "MEDICAL" if norm in MEDICAL_KEYS else "PRIVATE_PAY" if norm in PRIVATE_PAY_KEYS else "PERSON_ATTRIBUTE"
                    result[key] = self._replace(kind, item) if isinstance(item, (str, int)) else self._walk(item, path + (key,))
                elif norm in LOCAL_METADATA_KEYS and isinstance(item, str) and ABS_LOCAL_RE.match(item):
                    result[key] = self._replace("LOCAL_PATH", item)
                else:
                    result[key] = self._walk(item, path + (key,))
            return result
        if isinstance(value, list):
            return [self._walk(item, path + (index,)) for index, item in enumerate(value)]
        if isinstance(value, str):
            if value.lstrip().startswith(("{", "[")):
                try:
                    decoded = json.loads(value)
                except (ValueError, RecursionError):
                    decoded = None
                if isinstance(decoded, (dict, list)):
                    cleaned = self._walk(decoded, path + ("embedded_json",))
                    return json.dumps(cleaned, ensure_ascii=False, separators=(",", ":")) if cleaned != decoded else value
            return self.clean_text(value)
        return value

    def _strings(self, value, path=()):
        if isinstance(value, dict):
            for key, item in value.items():
                if not path and key in {"tools", "privacy_review"}:
                    continue
                yield from self._strings(item, path + (key,))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                yield from self._strings(item, path + (index,))
        elif isinstance(value, str):
            yield value

    def postscan(self, value) -> dict:
        counts = Counter()
        flags = self._structured_person_flags(value)
        for text in self._strings(value):
            for pattern, name in ((PHONE_RE, "phone_pattern"), (ID_RE, "government_id_pattern"), (SECRET_TOKEN_RE, "credential_token"), (JWT_RE, "jwt"), (UNTERMINATED_KEY_RE, "private_key_block")):
                counts[name] += sum(not self._safe(m.group(0)) for m in pattern.finditer(text))
            counts["nonreserved_email"] += sum(m.group(0).rsplit("@", 1)[1].lower() not in RESERVED_DOMAINS and not m.group(0).rsplit("@", 1)[1].lower().endswith(".invalid") for m in EMAIL_RE.finditer(text))
            for match in URL_RE.finditer(text):
                try:
                    parts = urlsplit(match.group(0))
                    counts["url_userinfo"] += int("@" in parts.netloc)
                    counts["url_secret_query"] += sum(_key(k) in SENSITIVE_QUERY_KEYS for k, v in parse_qsl(parts.query, keep_blank_values=True))
                except ValueError:
                    flags.add("unparsed_url")
            for match in COOKIE_ASSIGN_RE.finditer(text):
                counts["cookie_value"] += int(not self._safe(match.group(2)))
            for match in COOKIE_HEADER_RE.finditer(text):
                counts["cookie_header_value"] += int(not self._safe(match.group(2)))
            for match in PERSON_LABEL_RE.finditer(text):
                counts["labeled_person_name"] += int(not self._safe(match.group(2)))
            for match in CONTACT_HANDLE_LABEL_RE.finditer(text):
                counts["contact_handle"] += int(not self._safe(match.group(2)))
            if _name_candidates(text):
                flags.add("possible_remaining_resume_name")
            identity_or_placeholder = bool(PERSON_LABEL_RE.search(text) or PHONE_RE.search(text) or EMAIL_RE.search(text) or re.search(r"PERSON_[a-f0-9]{12}", text))
            biography_groups = sum(bool(pattern.search(text)) for pattern in BIOGRAPHY_GROUP_PATTERNS)
            if identity_or_placeholder and biography_groups >= 2 and (RESUME_HINT_RE.search(text) or re.search(r"工作经历|教育经历|毕业院校", text)):
                flags.add("resume_biographical_combination_requires_semantic_privacy_review")
            if identity_or_placeholder and PROTECTED_PERSONAL_VALUE_RE.search(text) and biography_groups:
                flags.add("personal_protected_attribute_combination_requires_review")
            for match in MEDICAL_RECORD_RE.finditer(text):
                value = re.split(r"[:：=]", match.group(0), maxsplit=1)[-1].strip()
                if not self._safe(value):
                    flags.add("possible_unstructured_personal_medical_record")
            if MEDIA_PAYLOAD_RE.search(text):
                flags.add("embedded_binary_or_media_payload")
        counts = Counter({k: v for k, v in counts.items() if v})
        if counts:
            flags.add("unresolved_known_sensitive_pattern")
        return {"status": "hold_for_review" if flags else "known_pattern_scan_clear", "remaining_pattern_counts": dict(counts), "risk_flags": sorted(flags), "not_complete_semantic_anonymization": True}

    def _structured_person_flags(self, value, path=()) -> set[str]:
        flags = set()
        if isinstance(value, dict):
            keys = {_key(k) for k in value}
            biography_groups = sum((bool(keys & EDUCATION_KEYS), bool(keys & EMPLOYMENT_KEYS), bool(keys & (PERSON_ATTRIBUTE_KEYS | PRIVATE_PAY_KEYS | MEDICAL_KEYS))))
            identity = bool(keys & (PERSON_KEYS | PERSON_CONTAINER_KEYS)) or ("name" in keys and bool(keys & (CONTACT_CONTEXT_KEYS | EDUCATION_KEYS | EMPLOYMENT_KEYS)))
            identity |= any(isinstance(v, str) and bool(re.fullmatch(r"PERSON_[a-f0-9]{12}", v)) for v in value.values())
            if identity and biography_groups >= 2:
                flags.add("structured_person_biographical_combination_requires_review")
            if identity and keys & (PERSON_ATTRIBUTE_KEYS | PRIVATE_PAY_KEYS | MEDICAL_KEYS):
                flags.add("structured_person_protected_attribute_combination_requires_review")
            for key, item in value.items():
                if not path and key in {"tools", "privacy_review"}:
                    continue
                flags.update(self._structured_person_flags(item, path + (key,)))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                flags.update(self._structured_person_flags(item, path + (i,)))
        elif isinstance(value, str) and value.lstrip().startswith(("{", "[")):
            try:
                decoded = json.loads(value)
            except (ValueError, RecursionError):
                decoded = None
            if isinstance(decoded, (dict, list)):
                flags.update(self._structured_person_flags(decoded, path + ("embedded_json",)))
        return flags

    def clean_row(self, row: dict) -> dict:
        cleaned = self.clean_value(row)
        assessment = self.postscan(cleaned)
        cleaned["privacy_review"] = {"schema_version": VERSION, **assessment}
        self.row_counts[assessment["status"]] += 1
        return cleaned

    def save_private_mapping(self) -> None:
        target = self.restricted_dir / "privacy_private_mapping.json"
        temporary = target.with_suffix(".tmp")
        value = {"schema_version": VERSION, "sensitive_local_only": True, "entries": list(self._mapping.values())}
        with self._lock:
            temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(target)

    def report(self) -> dict:
        return {"schema_version": VERSION, "replacement_counts": dict(self.counts), "unique_private_mapping_entries": len(self._mapping), "person_names_discovered": len(self._names), "discovery_calls": self.discovery_calls, "discovery_frozen": self.discovery_frozen, "row_assessments": dict(self.row_counts), "source_ids_pseudonymized": self.pseudonymize_source_ids, "salt_and_raw_mapping_in_restricted_directory_only": True, "original_bundle_modified": False, "claim": "Known structured fields and explicit text patterns transformed. Counts are transformation occurrences across calls/passes, not independent persons or rows. Clear pattern scan is not complete semantic anonymization or binary attachment clearance."}
