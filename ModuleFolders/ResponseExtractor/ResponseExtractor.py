import re
import string

# 回复解析器
class ResponseExtractor():
    def __init__(self):
        pass



    #处理并正则提取翻译内容
    def text_extraction(self, source_text_dict, html_string, target_language):

        try:
            # 提取译文结果
            translation_result= ResponseExtractor.extract_translation(self,source_text_dict,html_string)

            # 提取术语表结果
            glossary_result= ResponseExtractor.extract_glossary(self,html_string, target_language)

            # 提取禁翻表结果
            NTL_result = NTL_result = ResponseExtractor.extract_ntl(self,html_string)

            return translation_result, glossary_result, NTL_result
        except :
            print("\033[1;33mWarning:\033[0m 回复内容无法正常提取，请反馈\n")
            return {},{},{}


    # 提取翻译结果内容
    def extract_translation(self,source_text_dict,html_string):

        # 提取翻译文本
        text_dict = ResponseExtractor.label_text_extraction(self,html_string)

        if not text_dict:
            return {}  # 如果没有找到标签内容，返回空 JSON

        # 计算原文行数
        newlines_in_dict = ResponseExtractor.count_newlines_in_dict_values(self,source_text_dict)

        # 合并调整翻译文本
        translation_result= ResponseExtractor.generate_text_by_newlines(self,newlines_in_dict,text_dict)


        return translation_result


    # 辅助函数，正则提取标签文本内容
    def label_text_extraction(self, html_string):
        textarea_contents = re.findall(r'<textarea.*?>(.*?)</textarea>', html_string, re.DOTALL)
        if not textarea_contents:
            return {}  # 如果没有找到 textarea 标签，返回空字典

        output_dict = {}
        line_number = 0

        # 只处理最后一个 textarea 标签的内容
        last_content = textarea_contents[-1]
        lines = last_content.strip().splitlines()
        for line in lines:
            if line:
                output_dict[str(line_number)] = line
                line_number += 1

        # 如果没有找到任何以数字序号开头的行，则直接返回原始的行号字典（主要是为了兼容Sakura模型接口）
        has_numbered_prefix = False
        for value in output_dict.values():
            if re.match(r'^\d+\.', value):
                has_numbered_prefix = True
                break  # 只要找到一行符合条件就跳出循环

        # 从第一个以数字序号开头的行开始，保留之后的所有行(主要是有些AI会在译文内容前面加点说明)
        if has_numbered_prefix:
            filtered_dict = {}
            found = False
            # 按行号顺序遍历
            for key in sorted(output_dict.keys(), key=lambda k: int(k)):
                value = output_dict[key]
                if not found:
                    if re.match(r'^\d+\.', value):  # 匹配以数字和句点开头的行
                        found = True
                    else:
                        continue
                if found:
                    filtered_dict[key] = value
            return filtered_dict
        else:
            return output_dict  # 如果没有找到数字序号开头的行，则返回原始字典

    # 辅助函数，统计原文中的换行符
    def count_newlines_in_dict_values(self,source_text_dict):
        """
        统计字典中每个文本值内的换行符数量，并生成一个包含换行符统计结果的新字典。

        Args:
            source_text_dict: 输入字典，键为字符串，值为文本字符串。

        Returns:
            一个字典，键与输入字典相同，值为对应文本字符串中的换行符数量。
            例如：
            {'0': 0, '1': 1, '2': 0}
        """
        newline_counts = {}  # 初始化一个空字典用于存储换行符数量

        for key, text in source_text_dict.items():
            newline_count = text.count('\n')  # 使用字符串的count()方法统计换行符数量
            if newline_count == 0:
                newline_counts[key] = newline_count  # 将统计结果存入新字典，键保持不变
            else:
                newline_counts[key] = newline_count 
        return newline_counts

    # 辅助函数，根据换行符数量生成最终译文字典，与原文字典进行一一对应
    def generate_text_by_newlines(self, newline_counts_dict, translation_text_dict):
        """
        根据换行符统计字典和源文本字典生成新的字典，并处理多余内容。

        Args:
            newline_counts_dict: 换行符统计字典，键为字符串序号，值为换行符数量。
            translation_text_dict: 源文本字典，键为字符串序号，值为文本内容。

        Returns:
            一个新的字典，键与 newline_counts_dict 相同，值为根据换行符数量从 translation_text_dict
            中提取并拼接的文本内容。如果 translation_text_dict 内容不足，对应值为空字符串。
            如果 translation_text_dict 有剩余内容，将添加新键值对，键为最大原键加1，值为剩余内容按换行拼接。
        """
        result_dict = {}
        translation_keys_sorted = sorted(translation_text_dict.keys(), key=int)
        translation_index = 0

        # 处理每个预定键的行数需求
        for key, newline_count in newline_counts_dict.items():
            extracted_lines = []
            num_lines_to_extract = newline_count + 1 if newline_count > 0 else 1

            for _ in range(num_lines_to_extract):
                if translation_index < len(translation_keys_sorted):
                    current_key = translation_keys_sorted[translation_index]
                    extracted_lines.append(translation_text_dict[current_key])
                    translation_index += 1
                else:
                    break

            if extracted_lines:
                result_dict[key] = '\n'.join(extracted_lines) if newline_count > 0 else extracted_lines[0]
            else:
                result_dict[key] = ''

        # 添加剩余内容为新键值对
        if translation_index < len(translation_keys_sorted):
            if newline_counts_dict:
                max_key = max(map(int, newline_counts_dict.keys()))
            else:
                max_key = 0
            new_key = str(max_key + 1)
            remaining_texts = [translation_text_dict[k] for k in translation_keys_sorted[translation_index:]]
            result_dict[new_key] = '\n'.join(remaining_texts)

        return result_dict

    # 辅助函数，去除数字序号
    def remove_numbered_prefix(self,source_text_dict,translation_text_dict):
        """
        根据源文本的换行符数量，动态去除输入文本中对应的层级数字序号。
        
        逻辑说明：
        1. 源文本中换行符数量决定了序号层级（m个换行符对应m+1个子行）
        2. 主序号由字典键值+1决定（如键'0'的主序号是1，键'1'的主序号是2）
        3. 根据换行符数量选择匹配模式：
        - 无换行符：匹配"主序号."
        - 有换行符：匹配"主序号.子序号."
        """
        
        output_dict = {}
        for key, value in translation_text_dict.items():
            if not isinstance(value, str):
                output_dict[key] = value
                continue
            
            # 获取源文本的换行符数量
            source_text = source_text_dict.get(key, "")
            newline_count = source_text.count("\n")
            
            # 分割输入文本为多行处理
            lines = value.split("\n")
            cleaned_lines = []
            
            for line in lines:
                # 根据换行情况构建匹配模式
                if newline_count == 0:
                    # 匹配"主序号."模式（如"1."）
                    pattern = rf"^\d+\.\s*"  # 行首正则
                else:
                    # 匹配"主序号.子序号."模式（如"2.1."）
                    pattern = rf"^\d+\.\d+\.\s*"
                
                # 执行替换操作
                cleaned_line = re.sub(pattern, "", line)
                cleaned_lines.append(cleaned_line)
            
            # 重组处理后的文本
            output_dict[key] = "\n".join(cleaned_lines)
        
        return output_dict

    # 去除数字序号及括号
    def remove_numbered_prefix(self, source_text_dict, translation_text_dict):
        output_dict = {}
        for key, value in translation_text_dict.items():
            if not isinstance(value, str):
                output_dict[key] = value
                continue
            
            source_text = source_text_dict.get(key, "")
            source_lines = source_text.split('\n')
            translation_lines = value.split('\n')
            cleaned_lines = []
            
            for i, line in enumerate(translation_lines):

                # 去除数字序号 (只匹配 "1.", "1.2." 等)
                temp_line = re.sub(r'^\s*\d+\.(\d+\.)?\s*', '', line)

                source_line = source_lines[i] if i < len(source_lines) else ""
                
                # 计算源行开头的左括号数量
                stripped_source = source_line.lstrip()
                leading_source = 0
                for char in stripped_source:
                    if char in ('(', '（'):
                        leading_source += 1
                    else:
                        break
                
                # 计算源行结尾的右括号数量
                stripped_source_end = source_line.rstrip()
                trailing_source = 0
                for char in reversed(stripped_source_end):
                    if char in (')', '）'):
                        trailing_source += 1
                    else:
                        break
            
                # 处理译行开头的左括号
                leading_match = re.match(r'^(\s*)([\(\（]*)', temp_line)
                if leading_match:
                    space, brackets = leading_match.groups()
                    adjusted = brackets[:leading_source]
                    remaining = temp_line[len(space) + len(brackets):]
                    temp_line = f"{space}{adjusted}{remaining}"
                
                # 处理译行结尾的右括号
                trailing_match = re.search(r'([\)\）]*)(\s*)$', temp_line)
                if trailing_match:
                    brackets, space_end = trailing_match.groups()
                    adjusted = brackets[:trailing_source]
                    remaining = temp_line[:-len(brackets + space_end)] if (brackets + space_end) else temp_line
                    temp_line = f"{remaining}{adjusted}{space_end}"
                
                cleaned_lines.append(temp_line.strip())
            
            output_dict[key] = '\n'.join(cleaned_lines)
        
        return output_dict

    # 提取回复中的术语表内容
    def extract_glossary(self, text, target_language):
        """
        从文本中提取<character>标签内的术语表

        参数：
            text (str): 原始文本内容

        返回：
            list[tuple]: 包含(原文, 译文, 备注)的列表，没有匹配内容时返回空列表
        """
        # 匹配完整的character标签内容（支持多行内容）
        glossary_match = re.search(
            r'<character[^>]*>(.*?)</character>',  # 兼容标签属性
            text,
            re.DOTALL | re.IGNORECASE
        )

        if not glossary_match:
            return []

        content = glossary_match.group(1).strip()
        if not content:
            return []

        # 解析具体条目
        entries = []

        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue  # 跳过空行

            # 使用分隔符拆分字段（最多拆分成3个部分）
            parts = [part.strip() for part in line.split('|', 2)]

            # 有效性检查：至少需要原文和译文两个字段
            if len(parts) < 2:
                continue

            original, translation = parts[0], parts[1]
            comment = parts[2] if len(parts) >= 3 else ""



            # 检查并过滤错误内容
            if ResponseExtractor._is_invalid_glossary_entry(self,original, translation, comment, target_language):
                continue
            else:
                entries.append((original, translation, comment))

        return entries

    # 术语表过滤规则
    def _is_invalid_glossary_entry(self, original, translation, info, target_language):
        """判断条目是否需要过滤"""
        # 非空检查
        if not original.strip() :
            return True

        # 过滤表头行
        if original.strip().lower() in ("原文", "原名", "名字", "source", "original", "name"):
            return True

        # 过滤提取错行
        if translation.strip() in ("|"):
            return True

        # 过滤提取错行
        if (info) and (info.strip() in ("|")):
            return True

        # 过滤无翻译行
        if original.strip() == translation.strip():
            return True

        # 过滤翻译成罗马音(待改进，可以精简一个输入参数)
        if (target_language != "english") and (ResponseExtractor.is_pure_english_text(self,translation)):
            return True

        # 过滤过长行
        if len(original) > 20 or len(translation) > 20:
            return True

        # 过滤有点无语的东西
        if ResponseExtractor.should_filter(self,original):
            return True

        # 过滤下划线+随机英文+下划线文本内容，像“_HERO_”这样的内容
        if re.fullmatch(r'_([a-zA-Z]+)_', original):
            return True

        # 过滤随机英文+数字，像“P1”这样的内容
        if re.fullmatch(r'[a-zA-Z]\d+', original):
            return True

        # 过滤换行符或制表符
        if original == '\n' or original == '\t' or original == '\r':
            return True

        # 过滤纯数字（匹配整数）
        if re.fullmatch(r'^\d+$', original) :
            return True


        return False
    
    # 检查是否是人称代词
    def should_filter(self,original):
        """
        检查输入的字符串是否在要过滤的列表中。
        (Check if the input string is in the list to be filtered.)
        """

        pronouns_and_others_to_filter = {
            # == 无语的东西 ==
            "俺", "俺たち", "なし", "姉ちゃん", "男性", "彼女", "乙女", "彼", "ト", "僕", "我", "私",
            "你", "他", "她", "主人", # 中文代词也保留

            # == 补充的日语人称代词 ==
            # --- 第一人称 (单数) ---
            "わたくし",  # Watakushi (更正式/谦虚的 "我")
            "あたし",    # Atashi (非正式，通常女性使用)
            "わし",      # Washi (一些老年男性或方言中的 "我")
            "うち",      # Uchi (关西地区常用，有时年轻女性也用)
            "自分",      # Jibun ("自己"，有时用作第一人称)
            "小生",      # Shousei (男性自谦语，多用于书面)
            "我輩",      # Wagahai (较古老、自大的 "吾辈")

            # --- 第一人称 (复数) ---
            "私たち",    # Watashitachi ("我们"，通用)
            "わたくしたち",# Watakushitachi (更正式/谦虚的 "我们")
            "あたしたち",# Atashitachi (非正式，通常女性使用)
            "僕ら",      # Bokura ("我们"，男性，非正式)
            "僕たち",    # Bokutachi ("我们"，男性)
            "俺ら",      # Orera ("我们"，男性，非常非正式)
            # "俺たち" 已经在您的列表中
            "我々",      # Wareware ("我们"，非常正式，演讲、文章中常用)

            # --- 第二人称 (单数) ---
            "あなた",    # Anata ("你"，通用，但有时根据语境可能显得生疏或亲密)
            "あんた",    # Anta (Anata 的不礼貌/非常随意的形式)
            "君",        # Kimi ("你"，通常上级对下级、男性之间、或歌词中使用)
            "お前",      # Omae ("你"，非常随意，可能亲密也可能粗鲁)
            "貴様",      # Kisama ("你"，非常粗鲁，用于骂人)
            "そちら",    # Sochira ("您那边"，较礼貌的指代方式)
            "貴方",      # Anata (あなた 的汉字写法，通用)
            "貴女",      # Anata (あなた 的汉字写法，专指女性)
            "汝",        # Nanji/Nare (古语/文学作品中的 "你")

            # --- 第二人称 (复数) ---
            "あなたたち", # Anatatachi ("你们")
            "あなた方",  # Anatagata ("各位"，比 あなたたち 更礼貌)
            "あんたたち", # Antatachi (非正式的 "你们")
            "君たち",    # Kimitachi ("你们"，对下级或同辈)
            "君ら",      # Kimira (比 Kimitachi 更随意的 "你们")
            "お前たち",  # Omaetachi (随意的 "你们")
            "お前ら",    # Omaera (非常随意的 "你们")
            "貴様ら",    # Kisamara (粗鲁的 "你们")

            # --- 第三人称 (单数) ---
            # "彼" (Kare - 他/男友) 和 "彼女" (Kanojo - 她/女友) 已经在您的列表中
            "あの人",    # Ano hito ("那个人"，较常用且礼貌)
            "あの方",    # Ano kata ("那位"，更礼貌)
            "あいつ",    # Aitsu ("那家伙"，随意，可能不礼貌)
            "こいつ",    # Koitsu ("这家伙"，随意，可能不礼貌)
            "そいつ",    # Soitsu ("那家伙"，指离听者近的人/物，随意)

            # --- 第三人称 (复数) ---
            "彼ら",      # Karera ("他们"，可指男性群体或男女混合群体)
            "彼女ら",    # Kanojora ("她们"，专指女性群体，不如 彼ら 常用)
            "あの人たち",# Ano hitotachi ("那些人")
            "あの方々",  # Ano katagata ("那些位"，更礼貌)
            "あいつら",  # Aitsura ("那些家伙"，随意，可能不礼貌)
            "こいつら",  # Koitsura ("这些家伙"，随意，可能不礼貌)
            "そいつら",  # Soitsura ("那些家伙"，指离听者近的，随意)
        }

        if original.lower() in pronouns_and_others_to_filter:
            return True
        return False



    # 检查是否纯英文
    def is_pure_english_text(self,text):
        """
        检查给定的文本是否为纯英文字母（允许空格和换行符）。

        Args:
            text: 要检查的文本字符串。

        Returns:
            如果文本是纯英文字母，则返回 True，否则返回 False。
        """
        for char in text:
            if char not in string.ascii_letters and char != ' ' and char != '\n':
                return False
        return True

    # 提取回复中的禁翻表内容
    def extract_ntl(self, text):
        """
        从文本中提取<code>标签内的术语表

        参数：
            text (str): 原始文本内容

        返回：
            list[tuple]: 包含(原文, 译文, 备注)的列表，没有匹配内容时返回空列表
        """
        # 匹配完整的code>标签内容（支持多行内容）
        code_match = re.search(
            r'<code[^>]*>(.*?)</code>',  # 兼容标签属性
            text,
            re.DOTALL | re.IGNORECASE
        )

        if not code_match:
            return []

        content = code_match.group(1).strip()
        if not content:
            return []

        # 解析具体条目
        entries = []

        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue  # 跳过空行

            # 使用分隔符拆分字段（最多拆分成2个部分）
            parts = [part.strip() for part in line.split('|', 1)]

            # 有效性检查：至少需要原文和译文两个字段
            if len(parts) < 1:
                continue

            original = parts[0]
            info = parts[1] if len(parts) >= 2 else ""


            # 检查并过滤错误内容
            if ResponseExtractor._is_invalid_NTL_entry(self,original, info):
                continue
            else:
                entries.append((original, info))

        return entries

    # 禁翻表过滤规则
    def _is_invalid_NTL_entry(self, original, info):
        """判断条目是否需要过滤"""
        # 非空检查
        if not original.strip() :
            return True

        # 过滤表头行
        if original.lower() in ("markers", "标记符", "备注","原文", "source"):
            return True

        # 过滤提取错行
        if info.lower() in ("|"):
            return True

        # 过滤常见符号
        if original.strip() in ("#","「","」","『","』","※","★","？","！","～","…","♥","♡","^^","『』","♪","･･･","ー","（ ）","!!","无","\\n"):
            return True

        # 过滤换行符或制表符
        if original.strip() == '\n' or original.strip() == '\t' or original.strip() == '\r':
            return True

        # 过滤纯数字（匹配整数）
        if re.fullmatch(r'^\d+$', original):
            return True

        # 过滤纯英文（匹配大小写字母组合）
        if re.fullmatch(r'^[a-zA-Z]+$', original):
            return True

        # 新增：过滤被方括号/中文括号包围的数字（如[32]、【57】）
        if re.fullmatch(r'^[\[【]\d+[\]】]$', original):
            return True

        # 新增：过滤纯英文字母和数字的组合（如abc123）
        if re.fullmatch(r'^[a-zA-Z0-9]+$', original):
            return True

        return False