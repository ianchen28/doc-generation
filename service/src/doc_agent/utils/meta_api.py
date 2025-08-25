import re

from doc_agent.core.logger import logger
from doc_agent.utils import redis_meta_client

data_platform_mappings = {
    "standard": 0,
    "thesis": 1,
    "book": 2,
    "other": 4,
    "policy": 5,
    "executivevoice": 6,
    "announcement": 7
}


class MetaApi:
    """
    语料Meta信息查询接口实现
    """

    def __init__(self):
        pass

    def get_meta_info(self, query_list: list[dict]) -> dict:
        '''
        query_list 为list[dict]，每个dict包含dataType和tokenList
            dataType: 文件类型，0规范，1论文，2书籍，3公文，4其它，5企业制度6，高层声音，7全院公告，8企业报刊
            tokenList: 文件token列表
        返回值为dict: {
            "filetoken1": {
                "code": "文件编码",
                "file_name": "文件名称",
                "file_type": "文件类型"
            },
            "filetoken2": {
                "code": "文件编码",
                "file_name": "文件名称",
                "file_type": "文件类型"
            },
            ...
        }
        '''

        # 参数验证和标准化
        for query in query_list:
            if 'data_type' in query and 'dataType' not in query:
                query['dataType'] = query.pop('data_type')
            if 'token_list' in query and 'tokenList' not in query:
                query['tokenList'] = query.pop('token_list')

            if not isinstance(query.get('dataType'), int):
                raise ValueError("dataType must be a int")
            if not isinstance(query.get('tokenList'), list) or not all(
                    isinstance(item, str) for item in query.get('tokenList')):
                raise ValueError("tokenList must be a list of strings")

        # 收集所有需要查询的fileToken
        all_file_tokens = []
        token_to_datatype = {}  # 保存token和dataType的映射，用于后续的规范编号提取

        for query in query_list:
            data_type = query.get('dataType')
            for token in query.get('tokenList', []):
                all_file_tokens.append(token)
                token_to_datatype[token] = data_type

        if not all_file_tokens:
            return {}

        # 1. 优先从Redis获取元信息
        redis_results = redis_meta_client.get_meta_info_from_redis(
            all_file_tokens)

        # 2. 处理Redis返回的原始数据，转换为标准格式
        converted_redis_results = {}
        for token, redis_data in redis_results.items():
            if isinstance(redis_data, dict):
                # 获取解析后的metaInfo
                parsed_meta_info = redis_data.get('parsed_metaInfo', {})
                # 确保parsed_meta_info是字典类型
                if not isinstance(parsed_meta_info, dict):
                    logger.warning(
                        f"parsed_meta_info不是字典类型，token: {token}, 类型: {type(parsed_meta_info)}, 值: {parsed_meta_info}"
                    )
                    parsed_meta_info = {}
                # 转换为标准格式
                converted_result = self._convert_redis_to_standard_format(
                    redis_data, parsed_meta_info, token_to_datatype.get(token))
                converted_redis_results[token] = converted_result

        # 更新redis_results为转换后的结果
        redis_results = converted_redis_results

        # 5. 合并Redis和HTTP接口的结果
        final_results = {}
        final_results.update(redis_results)
        # final_results.update(http_results)

        return final_results

    def _convert_redis_to_standard_format(self, redis_data: dict,
                                          meta_info: dict,
                                          data_type: int) -> dict:
        """
        将Redis原始数据转换为标准格式
        
        Args:
            redis_data: 从Redis获取的原始数据
            meta_info: 解析后的metaInfo对象
            data_type: 文件数据类型
            
        Returns:
            dict: 标准格式的元信息
        """
        code = meta_info.get('code')
        file_name = redis_data.get('fileName')
        show_name = redis_data.get('showName')
        file_type = redis_data.get('fileType')

        # 如果是规范类型且没有code，尝试从文件名提取
        if data_type == 0 and (not code or code == ""):
            extracted_code = self._extract_standard_code(file_name)
            if extracted_code:
                code = extracted_code

        return {"code": code, "file_name": show_name, "file_type": file_type}

    def _extract_meta_info(self, meta_info: dict) -> dict:
        data = meta_info.get('data')

        if not isinstance(data, list):
            return {}

        result = {}
        for item in data:
            result[item.get('fileToken')] = self._process_file_meta_detailed(
                item)
        return result

    def _process_file_meta_detailed(self, file_meta_info: dict) -> dict:
        '''
        处理文件元信息
        '''
        data_type = file_meta_info.get('dataType')
        code = file_meta_info.get('metaInfo', {}).get('code')
        file_name = file_meta_info.get('fileName')
        show_name = file_meta_info.get('showName')
        file_type = file_meta_info.get('fileType')

        if data_type == 0:  # 规范
            if code is None or code == "":
                # 从文件名中抽出标准规范编码
                extracted_code = self._extract_standard_code(file_name)
                if extracted_code:
                    code = extracted_code
        return {"code": code, "file_name": show_name, "file_type": file_type}

    def _extract_standard_code(self, file_name: str) -> str:
        '''
        从文件名中提取规范编号
        规范编号为大写英文字母和数字的组合，中间可能存在空格、斜杠/、连接符-、括号中的数字
        '''
        if not file_name:
            return ""

        # 先将全角字符转换为半角字符
        file_name = file_name.replace('∕', '/').replace('－', '-').replace(
            '（', '(').replace('）', ')')

        # 匹配规范编号的正则表达式
        # 支持多种格式：GB/T、ISO、ASTM、JIS、EN、BS、DIN、ANSI等
        patterns = [
            # 标准格式：GB/T 1234-2019, ISO 9001(2015), ASTM D123-45等
            r'[A-Z]{2,}[/∕]?[A-Z]*\s*[0-9]+(?:[.\-][0-9]+)*(?:\([0-9]{4}\)|\-[0-9]{4})?',
            # 简单格式：ABC123, XYZ456等
            r'[A-Z]{2,}[0-9]+(?:[.\-][0-9]+)*',
            # 带空格的格式：GB T 1234, ISO 9001等
            r'[A-Z]{2,}\s+[A-Z]*\s*[0-9]+(?:[.\-][0-9]+)*(?:\([0-9]{4}\)|\-[0-9]{4})?'
        ]

        all_matches = []
        for pattern in patterns:
            matches = re.findall(pattern, file_name)
            all_matches.extend(matches)

        if all_matches:
            # 返回最长的匹配项（通常是最完整的规范编号）
            longest_match = max(all_matches, key=len)
            # 清理首尾空格并标准化分隔符
            result = longest_match.strip()
            # 将全角斜杠统一为半角
            result = result.replace('∕', '/')
            return result

        return ""


meta_api = MetaApi()


def update_doc_meta_data(docs: list):
    '''
    获取文档的id和domain_ids，并根据data_platform_mappings转换后调用meta_api.get_meta_info
    '''
    # 按数据类型分组文档
    docs_by_type = {}

    for doc in docs:
        file_token = doc.get('doc_id')
        domain_id = doc.get('domain_id')

        # 根据data_platform_mappings获取对应的dataType
        data_type = data_platform_mappings.get(domain_id, None)  # 默认为4(其他)
        if data_type is None:
            continue

        # 获取token，假设文档中有token字段
        if file_token:
            if data_type not in docs_by_type:
                docs_by_type[data_type] = []
            docs_by_type[data_type].append(file_token)

    # 构建query_list用于调用meta_api.get_meta_info
    query_list = []
    for data_type, tokens in docs_by_type.items():
        if tokens:  # 确保有token才添加
            query_list.append({"dataType": data_type, "tokenList": tokens})

    # 调用meta_api.get_meta_info获取元信息
    meta_info = {}
    if query_list:
        meta_info = meta_api.get_meta_info(query_list)

    # 将元信息更新到对应的文档中的meta_data字段
    for doc in docs:
        doc_id = doc.get('doc_id')
        if doc_id and doc_id in meta_info:
            # 更新原有的meta_data字段
            if 'meta_data' not in doc:
                doc['meta_data'] = {}
            meta_data_update = meta_info[doc_id]

            # 去除值为None的键
            meta_data_update = {
                k: v
                for k, v in meta_data_update.items() if v is not None
            }

            doc['meta_data'].update(meta_data_update)

    return docs


if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("API调用测试")
    print("=" * 60)

    # 原有的API测试
    print(
        meta_api.get_meta_info([{
            "dataType":
            2,
            "tokenList": [
                "227f0440b01308e5c58b27f4ea3ded99",
                "2754e22e122169a900c388ee51b2335911"
            ]
        }]))

    print("\n" + "=" * 60)
    print("get_doc_id_and_domain_ids测试")
    print("=" * 60)
