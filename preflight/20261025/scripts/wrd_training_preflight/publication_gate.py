"""Conservative publication gate for tabular text with unlinked personal fields.

This is a separate gate after privacy.Sanitizer, not a de-identification claim.
Spreadsheet cell extraction separates headers from values; a clean regex scan
therefore cannot establish that the column values were transformed correctly.
No original values, filenames, or source paragraphs appear in the result.
"""
from __future__ import annotations

from collections import Counter
import json
import re


VERSION = "wrd-tabular-publication-gate-v1"

HEADERS = {
    "identity": {
        "姓名", "真实姓名", "员工姓名", "人员姓名", "联系人", "联系人姓名",
        "候选人姓名", "求职者姓名", "患者姓名", "收件人", "户名", "姓名name",
        "职工姓名", "客户姓名", "经办人", "申请人", "申请人姓名", "负责人",
        "fullname", "realname", "personname", "employeename", "patientname",
        "candidatename", "applicantname", "contactname", "recipientname",
        "name", "firstname", "lastname", "gender", "sex", "age", "dob",
        "性别", "年龄", "出生日期", "出生年月", "身份证", "身份证号", "身份证号码",
        "护照号", "社保号", "nationalid", "idnumber", "passportnumber", "dateofbirth",
        "联系电话", "电话号码", "电话", "手机号", "手机号码", "手机", "联系方式",
        "邮箱", "电子邮箱", "电子邮件", "微信", "微信号", "qq", "qq号",
        "phone", "phonenumber", "mobile", "telephone", "email", "emailaddress", "wechat",
        "家庭住址", "个人住址", "联系地址", "通讯地址", "邮寄地址", "homeaddress",
    },
    "bank_account": {
        "银行卡", "银行卡号", "银行账号", "银行帐号", "银行账户", "收款账号",
        "收款账户", "付款账号", "付款账户", "账户号码", "开户账号", "开户帐号",
        "开户行", "开户银行", "持卡人", "收款人", "收款人姓名", "领款人",
        "bankaccount", "bankaccountnumber", "cardnumber", "iban", "routingnumber",
    },
    "private_pay": {
        "当前薪资", "目前薪资", "期望薪资", "个人收入", "年收入", "工资流水",
        "薪资", "工资", "月薪", "年薪", "实发工资", "应发工资", "税后工资",
        "基本工资", "个人所得税", "应纳个税", "薪酬", "社保基数", "公积金基数",
        "currentsalary", "expectedsalary", "personalincome", "annualincome", "salary",
    },
    "protected_attribute": {
        "民族", "宗教", "婚姻状况", "婚育状况", "婚育", "生育情况", "政治面貌",
        "政治身份", "性取向", "残疾情况", "孕产情况", "工会身份", "religion",
        "ethnicity", "maritalstatus", "politicalaffiliation", "sexualorientation",
    },
    "personal_medical_record": {
        "患者姓名", "诊断结果", "诊断", "病历号", "病史", "疾病史", "既往史",
        "既往病史", "体检结果", "患者病史", "健康状况", "用药记录", "住院号",
        "medicalrecordnumber", "patienthistory", "diagnosisresult", "diagnosis",
    },
    "resume_biography": {
        "简历", "简历名称", "简历编号", "求职意向", "求职状态", "应聘岗位",
        "候选人", "教育经历", "工作经历", "任职经历", "毕业院校", "毕业学校",
        "毕业时间", "工作年限", "工作经验", "resume", "candidate", "educationhistory",
        "workhistory", "workexperience", "employmenthistory",
    },
}
LOOKUP = {header: kind for kind, headers in HEADERS.items() for header in headers}
ANNOTATION_RE = re.compile(r"[（(\[【][^）)\]】]{0,60}[）)\]】]")
NORMALIZE_RE = re.compile(r"[\s_.\-:：*＊/\\]+")
CELL_KEY_RE = re.compile(r'"(?:cell|stored_value)"\s*:')
XLSX_MARKER_RE = re.compile(r"\[xl/(?:workbook\.xml|worksheets/sheet\d+\.xml)|formulas_not_evaluated|xl/sharedStrings\.xml", re.I)
# Only bounded, potential header strings are examined; no splitlines() or
# unbounded JSON-value pattern over a gigabyte-sized worksheet text.
HEADER_VALUE_RE = re.compile(
    r'"(?:stored_value|column_name|columnName|header|表头|列名)"\s*:\s*'
    r'"((?:[^"\\]|\\.){1,160})"'
)
HEADER_LINE_RE = re.compile(r"(?m)^[^\r\n]{0,220}[\t|,，][^\r\n]{0,220}$")
DELIMITERS_RE = re.compile(r"\t|\||,|，|;|；")
LITERAL_HEADER_ARRAY_KEYS = {"columns", "columnnames", "headers", "header", "表头", "列名", "字段名"}
CELL_KEYS = {"cell", "storedvalue", "formula", "type"}


def normalize(value: str) -> str:
    return NORMALIZE_RE.sub("", ANNOTATION_RE.sub("", value.strip())).lower()


def header_kind(value) -> str | None:
    if not isinstance(value, str) or len(value) > 200:
        return None
    if value.isdecimal():
        return None
    return LOOKUP.get(normalize(value))


def assess(value) -> dict:
    """Return a publication hold for personal-header table text, with no raw PII.

    Walks all representations, including SFT prompt/tool strings and embedded
    JSON. A bare XLSX path or generic health-industry text is not table content.
    Finding one such header is sufficient: column-value linkage has not been
    reviewed. Pure business/numeric tables remain eligible for other gates.
    """
    counts = Counter()

    def mark(kind, location):
        if kind:
            counts[kind] += 1
            counts["evidence:" + location] += 1
            return True
        return False

    def text_scan(text):
        cell_text = bool(CELL_KEY_RE.search(text))
        xlsx_text = bool(XLSX_MARKER_RE.search(text))
        if cell_text:
            for match in HEADER_VALUE_RE.finditer(text):
                raw = match.group(1)
                if "\\" in raw:
                    try:
                        raw = json.loads('"' + raw + '"')
                    except (ValueError, RecursionError):
                        continue
                if mark(header_kind(raw), "cell_header_text"):
                    return True
            if xlsx_text:
                # This extractor's worksheet values are all represented as
                # cell/stored_value entries above. Do not re-tokenize every
                # cell as a CSV line after an exhaustive header scan.
                return False
        # Markdown/TSV/CSV table headers may appear in native tool observations
        # without Office metadata. Exact header tokens avoid medical topic prose.
        for match in HEADER_LINE_RE.finditer(text):
            line = match.group(0)
            parts = [x.strip(" `\"'") for x in DELIMITERS_RE.split(line) if x.strip()]
            categories = [header_kind(part) for part in parts]
            found = [category for category in categories if category]
            if found and (xlsx_text or "\t" in line or "|" in line or len(found) >= 2):
                mark(found[0], "delimited_header_text")
                return True
        return False

    def walk(item, parent_key=""):
        if isinstance(item, dict):
            keys = {normalize(str(key)) for key in item}
            if "cell" in keys and ("storedvalue" in keys or "formula" in keys):
                for key, child in item.items():
                    if normalize(str(key)) == "storedvalue" and mark(header_kind(child), "structured_cell_header"):
                        return True
            # Column-bearing records and explicit header arrays retain linkage
            # cues even after ordinary field-level de-identification.
            if parent_key in {"rows", "records", "data", "table", "entries"}:
                for key in item:
                    if mark(header_kind(str(key)), "structured_table_column"):
                        return True
            for key, child in item.items():
                norm = normalize(str(key))
                if norm in LITERAL_HEADER_ARRAY_KEYS and isinstance(child, list):
                    for header in child:
                        if mark(header_kind(header), "structured_header_array"):
                            return True
                if walk(child, norm):
                    return True
        elif isinstance(item, list):
            for child in item:
                if isinstance(child, dict) and not ({normalize(str(k)) for k in child} & CELL_KEYS):
                    for key in child:
                        if mark(header_kind(str(key)), "structured_table_column"):
                            return True
                if walk(child, parent_key):
                    return True
        elif isinstance(item, str):
            if text_scan(item):
                return True
            # A bounded embedded JSON decoder covers typical tool arguments.
            # Large cell dumps are already scanned above; avoid a second GB
            # parse/copy merely because their first character is '['.
            if len(item) <= 8 * 1024 * 1024 and item.lstrip().startswith(("{", "[")):
                try:
                    decoded = json.loads(item)
                except (ValueError, RecursionError):
                    decoded = None
                if isinstance(decoded, (dict, list)) and walk(decoded, parent_key):
                    return True
        return False

    held = walk(value)
    return {
        "schema_version": VERSION,
        "status": "hold_for_review" if held else "no_sensitive_tabular_header_detected",
        "risk_flags": ["tabular_personal_columns_not_linked_for_anonymization"] if held else [],
        "evidence_counts": dict(counts),
        "not_complete_semantic_anonymization": True,
        "raw_values_not_reported": True,
    }


def preassess(value) -> dict:
    """Same gate for a raw row, before discovery/cleaning large held tables.

    A hold authorizes only a controlled original reference and metadata in the
    caller's manifest. It does not authorize publishing/copying the text body.
    Passing this gate never skips the caller's full discovery, cleaning, and
    postscan; it merely found no recognized sensitive table header.
    """
    return assess(value)
