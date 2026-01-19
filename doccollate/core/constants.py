CHECKED_SYMBOL = "\u2611"
UNCHECKED_SYMBOL = "\u2610"

CELL_MAP_TEXT = {
    "product__service_object": (0, "B2"),
    "product__main_functions": (0, "B3"),
    "product__tech_specs": (0, "B4"),
    "app__product_type_text": (0, "B5"),
    "env__memory_req": (1, "B3"),
    "env__hardware_model": (1, "E3"),
    "env__os": (1, "B8"),
    "env__language": (1, "E8"),
    "env__database": (1, "B9"),
    "env__soft_scale": (1, "E9"),
    "env__os_version": (1, "B10"),
    "env__hw_dev_platform": (1, "C12"),
    "env__sw_dev_platform": (1, "C14"),
    "assess__workload": (2, "C7"),
    "app__category_assess": (2, "B10"),
    "assess__dev_date": (2, "C5"),
    "assess__completion_date": (2, "C6"),
}

CELL_MAP_CHECKBOX = {
    "assess__support_floppy": (1, "A4"),
    "assess__support_sound": (1, "D4"),
    "assess__support_cdrom": (1, "A5"),
    "assess__support_gpu": (1, "D5"),
    "assess__support_other": (1, "A6"),
    "assess__is_self_dev": (2, "A2"),
    "assess__has_docs": (2, "A3"),
    "assess__has_source": (2, "A4"),
}

CELL_MODE_PURE = (2, "C8")
CELL_MODE_EMBEDDED = (2, "C9")

WRAP_TEXT_KEYS = {
    "product__service_object",
    "product__main_functions",
    "product__tech_specs",
    "app__product_type_text",
    "env__os",
    "env__hw_dev_platform",
    "env__sw_dev_platform",
    "app__category_assess",
}

PRODUCT_TYPE_PREFIX = {
    "Operating System": "\u7cfb\u7edf\u8f6f\u4ef6-",
    "Chinese Processing System": "\u7cfb\u7edf\u8f6f\u4ef6-",
    "Network System": "\u7cfb\u7edf\u8f6f\u4ef6-",
    "Embedded Operating System": "\u7cfb\u7edf\u8f6f\u4ef6-",
    "Other(System)": "\u7cfb\u7edf\u8f6f\u4ef6-",
    "Programming Language": "\u652f\u6301\u8f6f\u4ef6-",
    "Database System Design": "\u652f\u6301\u8f6f\u4ef6-",
    "Tools": "\u652f\u6301\u8f6f\u4ef6-",
    "Network Communication Software": "\u652f\u6301\u8f6f\u4ef6-",
    "Middleware": "\u652f\u6301\u8f6f\u4ef6-",
    "Other(Support)": "\u652f\u6301\u8f6f\u4ef6-",
    "Industry Management Software": "\u5e94\u7528\u8f6f\u4ef6-",
    "Office Software": "\u5e94\u7528\u8f6f\u4ef6-",
    "Pattern Recognition Software": "\u5e94\u7528\u8f6f\u4ef6-",
    "Graphics Software": "\u5e94\u7528\u8f6f\u4ef6-",
    "Control Software": "\u5e94\u7528\u8f6f\u4ef6-",
    "Network Application Software": "\u5e94\u7528\u8f6f\u4ef6-",
    "Information Management Software": "\u5e94\u7528\u8f6f\u4ef6-",
    "Database Management Application Software": "\u5e94\u7528\u8f6f\u4ef6-",
    "Security and Confidentiality Software": "\u5e94\u7528\u8f6f\u4ef6-",
    "Embedded Application Software": "\u5e94\u7528\u8f6f\u4ef6-",
    "Education Software": "\u5e94\u7528\u8f6f\u4ef6-",
    "Game Software": "\u5e94\u7528\u8f6f\u4ef6-",
}

PRODUCT_TYPE_CN = {
    "Operating System": "\u64cd\u4f5c\u7cfb\u7edf",
    "Chinese Processing System": "\u4e2d\u6587\u5904\u7406\u7cfb\u7edf",
    "Network System": "\u7f51\u7edc\u7cfb\u7edf",
    "Embedded Operating System": "\u5d4c\u5165\u5f0f\u64cd\u4f5c\u7cfb\u7edf",
    "Other(System)": "\u5176\u4ed6",
    "Programming Language": "\u7a0b\u5e8f\u8bbe\u8ba1\u8bed\u8a00",
    "Database System Design": "\u6570\u636e\u5e93\u7cfb\u7edf\u8bbe\u8ba1",
    "Tools": "\u5de5\u5177\u8f6f\u4ef6",
    "Network Communication Software": "\u7f51\u7edc\u901a\u4fe1\u8f6f\u4ef6",
    "Middleware": "\u4e2d\u95f4\u4ef6",
    "Other(Support)": "\u5176\u4ed6",
    "Industry Management Software": "\u884c\u4e1a\u7ba1\u7406\u8f6f\u4ef6",
    "Office Software": "\u529e\u516c\u8f6f\u4ef6",
    "Pattern Recognition Software": "\u6a21\u5f0f\u8bc6\u522b\u8f6f\u4ef6",
    "Graphics Software": "\u56fe\u5f62\u56fe\u8c61\u8f6f\u4ef6",
    "Control Software": "\u63a7\u5236\u8f6f\u4ef6",
    "Network Application Software": "\u7f51\u7edc\u5e94\u7528\u8f6f\u4ef6",
    "Information Management Software": "\u4fe1\u606f\u7ba1\u7406\u8f6f\u4ef6",
    "Database Management Application Software": "\u6570\u636e\u5e93\u7ba1\u7406\u5e94\u7528\u8f6f\u4ef6",
    "Security and Confidentiality Software": "\u5b89\u5168\u4e0e\u4fdd\u5bc6\u8f6f\u4ef6",
    "Embedded Application Software": "\u5d4c\u5165\u5f0f\u5e94\u7528\u8f6f\u4ef6",
    "Education Software": "\u6559\u80b2\u8f6f\u4ef6",
    "Game Software": "\u6e38\u620f\u8f6f\u4ef6",
}

CATEGORY_ID_OPTIONS = {
    "01 \u64cd\u4f5c\u7cfb\u7edf",
    "02 \u5de5\u5177\u8f6f\u4ef6\u4e0e\u5e73\u53f0\u7cfb\u7edf",
    "03 \u4e2d\u95f4\u4ef6",
    "04 \u4fe1\u606f\u5b89\u5168",
    "05 \u5176\u5b83\u57fa\u7840\u8f6f\u4ef6",
    "06 \u4fe1\u606f\u901a\u8baf(ICT)",
    "07 \u6570\u5b57\u88c5\u5907",
    "08 \u533b\u7597\u8bbe\u5907",
    "09 \u5546\u7528\u53ca\u529e\u516c\u8bbe\u5907",
    "10 \u6570\u5b57\u7535\u89c6",
    "11 \u6c7d\u8f66\u7535\u5b50",
    "12 \u8ba1\u7b97\u673a\u53ca\u8bbe\u5907",
    "13 \u6d88\u8d39\u7535\u5b50",
    "14 \u4fe1\u606f\u5bb6\u7535",
    "15 \u5176\u4ed6\u901a\u8baf\u548c\u5de5\u4e1a",
    "16 \u529e\u516c\u548c\u7ba1\u7406",
    "17 \u4f01\u4e1a\u7ba1\u7406",
    "18 \u7535\u5b50\u653f\u52a1",
    "19 \u533b\u7597\u536b\u751f",
    "20 \u6559\u80b2",
    "21 \u5730\u7406\u4fe1\u606f",
    "22 \u91d1\u878d",
    "23 \u4ea4\u901a\u7269\u6d41",
    "24 \u6587\u5316\u521b\u610f",
    "25 \u5546\u8d38\u65c5\u6e38",
    "26 \u901a\u8baf\u7f51\u7edc\u670d\u52a1",
    "27 \u80fd\u6e90\u548c\u73af\u4fdd",
    "28 \u5efa\u7b51\u7269\u4e1a",
    "29 \u4e92\u8054\u7f51\u670d\u52a1",
    "30 \u5176\u4ed6\u8ba1\u7b97\u673a\u5e94\u7528\u8f6f\u4ef6\u548c\u4fe1\u606f\u670d\u52a1",
    "31 IC\u8bbe\u8ba1",
}

FIELD_PROMPTS = {
    "app__product_type": "提取软件所属类别/软件类别（中文短语），若无请输出空字符串。",
    "app__category_assess": "提取软件评估分类号（形如“01 操作系统”），若无请输出空字符串。",
    "product__service_object": "\u4ece\u672c\u6bb5\u63d0\u70bc\u670d\u52a1\u5bf9\u8c61\uff0c\u5199\u6210\u4e00\u53e5\u4e2d\u6587\u77ed\u8bed\uff0c\u4ec5\u8bf4\u660e\u9762\u5411\u4eba\u7fa4/\u7ec4\u7ec7\uff0c\u4e0d\u8981\u5199\u76ee\u7684\uff0c80-120\u5b57\u3002",
    "product__main_functions": "\u57fa\u4e8e\u6a21\u5757\u5217\u8868\u603b\u7ed3\u4e3b\u8981\u529f\u80fd\uff0c80-120\u5b57\uff0c\u9762\u5411\u4f7f\u7528\u573a\u666f\u3002",
    "product__tech_specs": "\u63d0\u70bc3-5\u6761\u6280\u672f\u6307\u6807\u5f0f\u63cf\u8ff0\uff0c\u4e2d\u6587\u77ed\u53e5\uff0c\u504f\u53ef\u9a8c\u8bc1\u7279\u6027\u3002",
    "product__app_domain": "\u63d0\u53d6\u5e94\u7528\u9886\u57df\uff0c\u4e2d\u6587\u77ed\u8bed\uff0c\u4e0d\u5e26\u82f1\u6587\u6216\u62ec\u53f7\u3002",
    "env__dev_platform": "\u6982\u62ec\u5f00\u53d1\u5e73\u53f0\uff0c30-60\u5b57\uff0c\u907f\u514d\u786c\u4ef6\u7ec6\u8282\uff0c\u53ea\u4fdd\u7559OS/\u4e3b\u8981\u5de5\u5177/\u6846\u67b6\u3002",
    "env__run_platform": "\u6982\u62ec\u8fd0\u884c\u5e73\u53f0\uff0c30-60\u5b57\uff0c\u4ec5\u8bf4\u660e\u8fd0\u884c\u64cd\u4f5c\u7cfb\u7edf/\u8fd0\u884c\u73af\u5883\u7c7b\u578b\uff0c\u4e0d\u8981\u5217\u914d\u7f6e\u3002",
    "env__hw_dev_platform": "\u63d0\u53d6\u5f00\u53d1\u786c\u4ef6\u73af\u5883\u63cf\u8ff0\uff0c\u4fdd\u6301\u539f\u59cb\u914d\u7f6e\u8981\u70b9\u3002",
    "env__sw_dev_platform": "\u63d0\u53d6\u5f00\u53d1\u8f6f\u4ef6\u73af\u5883/\u5de5\u5177\uff0c\u6309\u201cOS/\u5de5\u5177/\u6846\u67b6\u201d\u987a\u5e8f\u7b80\u8ff0\u3002",
    "env__memory_req": "\u63d0\u53d6\u5185\u5b58\u8981\u6c42\uff0c\u8f93\u51fa\u683c\u5f0f\u5982 512MB\u3002",
    "env__hardware_model": "\u63d0\u53d6\u9002\u7528\u673a\u578b\uff0c\u8f93\u51fa\u7b80\u77ed\u673a\u578b\u63cf\u8ff0\u3002",
    "env__os": "\u6982\u62ec\u8fd0\u884c\u64cd\u4f5c\u7cfb\u7edf\uff08\u53ef\u591a\u9879\uff09\uff0c\u82e5\u65e0\u660e\u786e\u4fe1\u606f\u8bf7\u8f93\u51fa\u7a7a\u5b57\u7b26\u4e32\u3002",
    "env__soft_scale": "\u63d0\u53d6\u8f6f\u4ef6\u89c4\u6a21\uff08\u5927/\u4e2d/\u5c0f\uff09\uff0c\u82e5\u65e0\u660e\u786e\u4fe1\u606f\u8bf7\u8f93\u51fa\u201c\u4e2d\u201d\u3002",
    "env__language": "\u63d0\u53d6\u7f16\u7a0b\u8bed\u8a00\uff0c\u4f7f\u7528\u539f\u6587\u540d\u79f0\uff0c\u5fc5\u987b\u8f93\u51fa\u5b8c\u6574\u540d\u5b57\uff0c\u4e0d\u5141\u8bb8\u7f29\u5199\u3002",
    "env__database": "\u63d0\u53d6\u6570\u636e\u5e93\u7c7b\u578b/\u7248\u672c\uff0c\u82e5\u591a\u9879\u53d6\u4e3b\u5e93\u3002",
    "env__os_version": "\u63d0\u53d6\u5f00\u53d1OS\u53ca\u7248\u672c\uff0c\u4fdd\u6301\u539f\u6587\u683c\u5f0f\u3002",
}

FIELD_TITLE_KEYWORDS = {
    "app__product_type": ["\u6240\u5c5e\u7c7b\u522b", "\u8f6f\u4ef6\u7c7b\u522b", "\u7c7b\u522b"],
    "app__category_assess": ["\u5206\u7c7b\u53f7", "\u8bc4\u4f30\u5206\u7c7b"],
    "product__service_object": ["\u5f00\u53d1\u76ee\u7684", "\u76ee\u6807", "\u5b9a\u4f4d"],
    "product__main_functions": ["\u4e3b\u8981\u529f\u80fd", "\u529f\u80fd\u67b6\u6784", "\u529f\u80fd\u8be6\u8ff0", "\u6a21\u5757"],
    "product__func_list": ["\u4e3b\u8981\u529f\u80fd", "\u529f\u80fd\u8be6\u8ff0", "\u6a21\u5757"],
    "product__tech_specs": ["\u6280\u672f\u7279\u70b9", "\u6280\u672f\u7279\u6027", "\u975e\u529f\u80fd\u6027", "\u6027\u80fd", "\u53ef\u9760\u6027", "\u6269\u5c55\u6027"],
    "product__app_domain": ["\u5e94\u7528\u9886\u57df", "\u5e94\u7528\u573a\u666f", "\u529f\u80fd"],
    "env__dev_platform": ["\u5f00\u53d1\u73af\u5883", "\u5f00\u53d1\u5e73\u53f0"],
    "env__run_platform": ["\u8fd0\u884c\u73af\u5883", "\u90e8\u7f72\u73af\u5883", "\u8f6f\u4ef6\u8fd0\u884c\u73af\u5883"],
    "env__hw_dev_platform": ["\u5f00\u53d1\u73af\u5883", "\u786c\u4ef6\u73af\u5883"],
    "env__sw_dev_platform": ["\u5f00\u53d1\u73af\u5883", "\u5f00\u53d1\u5de5\u5177", "\u8f6f\u4ef6\u5f00\u53d1\u73af\u5883"],
    "env__memory_req": ["\u8fd0\u884c\u73af\u5883", "\u786c\u4ef6", "\u786c\u4ef6\u73af\u5883"],
    "env__hardware_model": ["\u8fd0\u884c\u73af\u5883", "\u786c\u4ef6", "\u786c\u4ef6\u73af\u5883"],
    "env__os": ["\u64cd\u4f5c\u7cfb\u7edf", "\u8fd0\u884c\u73af\u5883"],
    "env__soft_scale": ["\u8f6f\u4ef6\u89c4\u6a21", "\u89c4\u6a21"],
    "env__language": ["\u5f00\u53d1\u73af\u5883", "\u5f00\u53d1\u8bed\u8a00", "\u6280\u672f\u6808"],
    "env__database": ["\u6570\u636e\u5e93", "\u5f00\u53d1\u73af\u5883", "\u8fd0\u884c\u73af\u5883", "\u6838\u5fc3\u6570\u636e\u5e93"],
    "env__os_version": ["\u5f00\u53d1\u73af\u5883", "\u64cd\u4f5c\u7cfb\u7edf"],
}

FIELD_QUERIES = {
    "app__product_type": "\u6240\u5c5e\u7c7b\u522b \u8f6f\u4ef6\u7c7b\u522b \u8f6f\u4ef6\u7c7b\u578b",
    "app__category_assess": "\u8bc4\u4f30\u5206\u7c7b\u53f7 \u8f6f\u4ef6\u5206\u7c7b\u53f7",
    "product__service_object": "\u670d\u52a1\u5bf9\u8c61 \u9762\u5411\u7528\u6237 \u76ee\u6807\u7fa4\u4f53 \u9002\u7528\u5bf9\u8c61",
    "product__main_functions": "\u4e3b\u8981\u529f\u80fd \u529f\u80fd\u67b6\u6784 \u6a21\u5757 \u529f\u80fd\u63cf\u8ff0",
    "product__func_list": "\u529f\u80fd\u6a21\u5757 \u4e3b\u8981\u529f\u80fd \u8be6\u8ff0 \u6a21\u5757\u540d\u79f0",
    "product__tech_specs": "\u6280\u672f\u6307\u6807 \u6280\u672f\u7279\u70b9 \u9ad8\u6027\u80fd \u9ad8\u53ef\u9760 \u53ef\u6269\u5c55 \u5b89\u5168",
    "product__app_domain": "\u5e94\u7528\u9886\u57df \u5e94\u7528\u573a\u666f \u884c\u4e1a",
    "env__dev_platform": "\u5f00\u53d1\u5e73\u53f0 \u5f00\u53d1\u73af\u5883 \u5de5\u5177 \u6846\u67b6",
    "env__run_platform": "\u8fd0\u884c\u5e73\u53f0 \u8fd0\u884c\u73af\u5883 \u90e8\u7f72\u5e73\u53f0",
    "env__hw_dev_platform": "\u5f00\u53d1\u786c\u4ef6 \u73af\u5883 \u914d\u7f6e",
    "env__sw_dev_platform": "\u5f00\u53d1\u5de5\u5177 \u6846\u67b6 IDE OS",
    "env__memory_req": "\u5185\u5b58\u8981\u6c42 \u5185\u5b58",
    "env__hardware_model": "\u9002\u7528\u673a\u578b \u786c\u4ef6 \u8bbe\u5907",
    "env__os": "\u8fd0\u884c\u64cd\u4f5c\u7cfb\u7edf \u8fd0\u884c\u73af\u5883 Windows Linux macOS",
    "env__soft_scale": "\u8f6f\u4ef6\u89c4\u6a21 \u5927 \u4e2d \u5c0f",
    "env__language": "\u5f00\u53d1\u8bed\u8a00 \u7f16\u7a0b\u8bed\u8a00 \u524d\u7aef \u540e\u7aef",
    "env__database": "\u6570\u636e\u5e93 \u7c7b\u578b \u7248\u672c MySQL PostgreSQL Oracle",
    "env__os_version": "\u64cd\u4f5c\u7cfb\u7edf \u7248\u672c",
}

SERVER_MODEL_POOL = [
    {
        "model": "Dell PowerEdge R750",
        "config": "CPU\uFF1AIntel Xeon Silver 4314\n\u5185\u5B58\uFF1A64GB\n\u786C\u76D8\uFF1A2TB SSD",
    },
    {
        "model": "HPE ProLiant DL380 Gen10",
        "config": "CPU\uFF1AIntel Xeon Gold 5218\n\u5185\u5B58\uFF1A128GB\n\u786C\u76D8\uFF1A4TB SSD",
    },
    {
        "model": "Lenovo ThinkSystem SR650",
        "config": "CPU\uFF1AIntel Xeon Silver 4216\n\u5185\u5B58\uFF1A64GB\n\u786C\u76D8\uFF1A2TB SSD",
    },
    {
        "model": "Inspur NF5280M5",
        "config": "CPU\uFF1AIntel Xeon Silver 4210\n\u5185\u5B58\uFF1A64GB\n\u786C\u76D8\uFF1A2TB SSD",
    },
    {
        "model": "Huawei FusionServer 2288H V5",
        "config": "CPU\uFF1AIntel Xeon Gold 6230\n\u5185\u5B58\uFF1A128GB\n\u786C\u76D8\uFF1A4TB SSD",
    },
    {
        "model": "Dell PowerEdge R740",
        "config": "CPU\uFF1AIntel Xeon Gold 5220\n\u5185\u5B58\uFF1A128GB\n\u786C\u76D8\uFF1A4TB SSD",
    },
    {
        "model": "HPE ProLiant DL360 Gen10",
        "config": "CPU\uFF1AIntel Xeon Silver 4210\n\u5185\u5B58\uFF1A64GB\n\u786C\u76D8\uFF1A2TB SSD",
    },
    {
        "model": "Lenovo ThinkSystem SR630",
        "config": "CPU\uFF1AIntel Xeon Silver 4214\n\u5185\u5B58\uFF1A64GB\n\u786C\u76D8\uFF1A2TB SSD",
    },
]

CLIENT_MODEL_POOL = [
    {
        "model": "Lenovo ThinkPad T14 Gen 4",
        "config": "CPU\uFF1AIntel Core i7-1360P\n\u5185\u5B58\uFF1A16GB\n\u786C\u76D8\uFF1A1TB SSD",
    },
    {
        "model": "Dell Precision 3660",
        "config": "CPU\uFF1AIntel Core i7-13700\n\u5185\u5B58\uFF1A32GB\n\u786C\u76D8\uFF1A1TB SSD",
    },
    {
        "model": "HP EliteDesk 800 G9",
        "config": "CPU\uFF1AIntel Core i5-13500\n\u5185\u5B58\uFF1A16GB\n\u786C\u76D8\uFF1A512GB SSD",
    },
    {
        "model": "Lenovo ThinkCentre M90t",
        "config": "CPU\uFF1AIntel Core i7-12700\n\u5185\u5B58\uFF1A16GB\n\u786C\u76D8\uFF1A1TB SSD",
    },
]

SERVER_OS_POOL = [
    "Windows Server 2019",
    "Windows Server 2022",
    "Ubuntu Server 20.04 LTS",
    "Ubuntu Server 22.04 LTS",
    "Red Hat Enterprise Linux 8.8",
    "Red Hat Enterprise Linux 9.2",
    "CentOS Stream 9",
    "SUSE Linux Enterprise Server 15 SP5",
    "Debian 11",
    "Debian 12",
    "\u94f6\u6cb3\u9e92\u9e9f\u9ad8\u7ea7\u670d\u52a1\u5668\u64cd\u4f5c\u7cfb\u7edf V10",
    "\u7edf\u4fe1UOS\u670d\u52a1\u5668\u7248 V20",
    "\u4e2d\u6807\u9e92\u9e9f\u9ad8\u7ea7\u670d\u52a1\u5668\u64cd\u4f5c\u7cfb\u7edf V7",
]

CLIENT_OS_POOL = [
    "Windows 10 \u4e13\u4e1a\u7248 22H2",
    "Windows 11 \u4e13\u4e1a\u7248 23H2",
    "macOS Ventura 13",
    "macOS Sonoma 14",
    "Ubuntu 22.04 LTS",
    "Ubuntu 24.04 LTS",
]

SERVER_SOFT_POOL = [
    "Nginx 1.24",
    "Apache HTTP Server 2.4",
    "Tomcat 9.0",
    "Tomcat 10.1",
    "Java 17 LTS",
    "Python 3.11",
    "Node.js 20 LTS",
    "PostgreSQL 13",
    "MySQL 8.0",
    "Redis 7.2",
]

CLIENT_SOFT_POOL = [
    "Chrome 120",
    "Edge 120",
    "Firefox 121",
    "Safari 17",
]

SERVER_CONFIG_POOL = [
    "CPU: Intel Xeon Silver 4314\n\u5185\u5b58: 64GB\n\u786c\u76d8: 2TB SSD",
    "CPU: Intel Xeon Gold 5318Y\n\u5185\u5b58: 128GB\n\u786c\u76d8: 2TB NVMe",
    "CPU: AMD EPYC 7313\n\u5185\u5b58: 64GB\n\u786c\u76d8: 2TB SSD",
    "CPU: Intel Xeon Silver 4210R\n\u5185\u5b58: 32GB\n\u786c\u76d8: 1TB SSD",
]

CLIENT_CONFIG_POOL = [
    "CPU: Intel Core i5-12400\n\u5185\u5b58: 16GB\n\u786c\u76d8: 512GB SSD",
    "CPU: Intel Core i7-12700\n\u5185\u5b58: 32GB\n\u786c\u76d8: 1TB SSD",
    "CPU: AMD Ryzen 5 5600\n\u5185\u5b58: 16GB\n\u786c\u76d8: 512GB SSD",
    "CPU: AMD Ryzen 7 5800X\n\u5185\u5b58: 32GB\n\u786c\u76d8: 1TB SSD",
]

MODULE_TITLE_WORDS = ["\u6a21\u5757", "\u5b50\u7cfb\u7edf", "\u5e73\u53f0", "\u4e2d\u5fc3", "\u540e\u53f0", "\u5de5\u4f5c\u53f0", "\u670d\u52a1", "\u7cfb\u7edf", "\u5e94\u7528", "\u8c03\u5ea6", "\u7ba1\u7406"]
MODULE_TEXT_HINTS = ["\u529f\u80fd\u6a21\u5757", "\u6a21\u5757\u5305\u62ec", "\u7cfb\u7edf\u5305\u62ec", "\u7cfb\u7edf\u7531", "\u4e3b\u8981\u6a21\u5757", "\u529f\u80fd\u7ec4\u6210"]
FALLBACK_MIN_MODULES = 3
