# -*- coding: utf-8 -*-

from workflow import Workflow3, ICON_WEB, web

import urllib,re,collections,xml.etree.ElementTree as ET
import sys
reload(sys)
sys.setdefaultencoding('utf8')

ICON_DEFAULT = 'icon.png'

PY3K = sys.version_info >= (3, 0)

def string_encode(word):
    if PY3K:
        return word
    else:
        return word.encode('utf-8')

def string_decode(word):
    if PY3K:
        return word
    else:
        return word.decode('utf-8')

def bytes_decode(word):
    if sys.version_info >= (3, 0):
        return word.decode()
    else:
        return word

WARN_NOT_FIND = string_decode(" 找不到该单词的释义")
ERROR_QUERY   = string_decode(" 有道翻译查询出错!")
NETWORK_ERROR = string_decode(" 无法连接有道服务器!")
QUERY_OK = string_decode("QUERY_OK")

def add_item_to_workflow(query, title, subtitle):
    arg = [query, title, query, '', '']
    arg = '$%'.join(arg)
    wf.add_item(
        title=title, subtitle=subtitle, arg=arg,
        valid=True, icon=ICON_DEFAULT)

QUERY_BLACK_LIST = ['.', '|', '^', '$', '\\', '[', ']', '{', '}', '*', '+',
        '?', '(', ')', '&', '=', '\"', '\'', '\t']

def preprocess_word(word):
    word = word.strip()
    for i in QUERY_BLACK_LIST:
        word = word.replace(i, ' ')
    array = word.split('_')
    word = []
    p = re.compile('[a-z][A-Z]')
    for piece in array:
        lastIndex = 0
        for i in p.finditer(piece):
            word.append(piece[lastIndex:i.start() + 1])
            lastIndex = i.start() + 1
        word.append(piece[lastIndex:])
    return ' '.join(word).strip()

def get_word_info(word):
    import json
    word = preprocess_word(word)
    if not word:
        return ''
    try:
        url = 'http://dict.youdao.com' + '/fsearch?q=' + urllib.quote(str(word))
        r = web.get(url)
        sys.stderr.write(r.content+'\n')
    except IOError:
        return NETWORK_ERROR
    if r.status_code == 200:
        doc = ET.fromstring(r.content)

        phrase = doc.find(".//return-phrase").text
        p = re.compile(r"^%s$"%word, re.IGNORECASE)
        if p.match(phrase):
            info = collections.defaultdict(list)

            if not len(doc.findall(".//content")):
                return WARN_NOT_FIND

            for el in doc.findall(".//"):
                if el.tag in ('return-phrase','phonetic-symbol'):
                    if el.text:
                        info[el.tag].append(el.text.encode("utf-8"))
                elif el.tag in ('content','value'):
                    if el.text:
                        info[el.tag].append(el.text.encode("utf-8"))

            if info["phonetic-symbol"]:
                for i in info["phonetic-symbol"]:
                    add_item_to_workflow(word, word + ' ['+i+']', '国际音标')

            if info["content"]:
                for i in info["content"]:
                    add_item_to_workflow(word, i, '词条解释')

            return QUERY_OK
        else:
            try:
                url = "http://fanyi.youdao.com" + "/translate?i=" + urllib.quote(str(word))
                r = web.get(url)
                sys.stderr.write(r.content+'\n')
            except IOError:
                return NETWORK_ERROR

            p = re.compile(r"global.translatedJson = (?P<result>.*);")

            r_result = bytes_decode(r.content)
            s = p.search(r_result)
            if s:
                r_result = json.loads(s.group('result'))
                if r_result is None:
                    return str_decode(s.group('result'))

                error_code = r_result.get("errorCode")
                if error_code is None or error_code != 0:
                    return str_decode(s.group('result'))

                translate_result = r_result.get("translateResult")
                if translate_result is None:
                    return str_decode(s.group('result'))

                translate_result_tgt = ''
                for i in translate_result:
                    translate_result_tgt = translate_result_tgt + i[0].get("tgt") + "\n"

                add_item_to_workflow(word, translate_result_tgt, '翻译结果')
                return QUERY_OK
            else:
                return ERROR_QUERY
    else:
        return  ERROR_QUERY

def main(wf):
    query = wf.args[0].strip().replace("\\", "")
    if not isinstance(query, unicode):
        query = query.decode('utf8')

    rt = get_word_info(query)
    if rt != QUERY_OK:
        add_item_to_workflow(query, rt, '错误')

    wf.send_feedback()

if __name__ == '__main__':
    wf = Workflow3()
    sys.exit(wf.run(main))
