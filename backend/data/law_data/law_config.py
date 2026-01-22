
from pathlib import Path

# Base directory relative to this config file
LAW_DATA_DIR = Path(__file__).parent

# List of law files to process
# Each entry contains:
# - name: Chinese name of the law
# - path: Relative path from LAW_DATA_DIR
# - prefix: The ID prefix used in articles (e.g., LSA, ENF_RULE)
LAW_FILES = [
    {
        "name": "勞動基準法",
        "path": "labor_standards_act.json",
        "prefix": "LSA"
    },
    {
        "name": "勞動基準法施行細則",
        "path": "subsidiary_laws/enforcement_rules.json",
        "prefix": "ENF_RULE"
    },
    {
        "name": "勞動部積欠工資墊償基金管理委員會組織規程",
        "path": "subsidiary_laws/wage_arrears_fund_mgmt_committee_org_rule.json",
        "prefix": "WAGE_ARREARS_FUND_COMM_ORG"
    },
    {
        "name": "積欠工資墊償基金提繳及墊償管理辦法",
        "path": "subsidiary_laws/wage_arrears_fund_collection_payment_reg.json",
        "prefix": "WAGE_ARREARS_FUND_PAY_REG"
    },
    {
        "name": "勞工請假規則",
        "path": "subsidiary_laws/labor_leave_rule.json",
        "prefix": "LEAVE_RULE"
    },
    {
        "name": "勞動基準法第四十五條無礙身心健康認定基準及審查辦法",
        "path": "subsidiary_laws/lsa_mind_body_health_determination_std.json",
        "prefix": "LSA_HEALTH_DETERMINATION"
    },
    {
        "name": "事業單位僱用女性勞工夜間工作場所必要之安全衛生設施標準",
        "path": "subsidiary_laws/female_labor_night_work_safety_std.json",
        "prefix": "FEMALE_NIGHT_SAFETY_STD"
    },
    {
        "name": "事業單位勞工退休準備金監督委員會組織準則",
        "path": "subsidiary_laws/ret_reserve_sup_committee_org.json",
        "prefix": "RET_RESERVE_SUP_COMM_ORG"
    },
    {
        "name": "勞工退休基金收支保管及運用辦法",
        "path": "subsidiary_laws/ret_fund_mgmt_reg.json",
        "prefix": "RET_FUND_MGMT_REG"
    },
    {
        "name": "勞工退休準備金提撥及管理辦法",
        "path": "subsidiary_laws/ret_reserve_alloc_mgmt_reg.json",
        "prefix": "RET_RESERVE_ALLOC_REG"
    },
    {
        "name": "勞工退休準備金資料提供金融機構處理辦法",
        "path": "subsidiary_laws/ret_reserve_fin_inst_data_reg.json",
        "prefix": "RET_RESERVE_FIN_INST_DATA"
    },
    {
        "name": "直轄市勞動檢查機構組織準則",
        "path": "subsidiary_laws/municipal_labor_inspection_inst_org_rule.json",
        "prefix": "MUNI_INSPECT_INST_ORG"
    },
    {
        "name": "勞動基準法檢舉案件保密及處理辦法",
        "path": "subsidiary_laws/lsa_report_confidentiality_proc_reg.json",
        "prefix": "LSA_REPORT_CONF_REG"
    },
    {
        "name": "勞資會議實施辦法",
        "path": "subsidiary_laws/labor_mgmt_meeting_impl_measure.json",
        "prefix": "LABOR_MGMT_MEETING_IMPL"
    }
]
