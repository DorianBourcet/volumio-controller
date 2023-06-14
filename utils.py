import re

def format_min_sec(seconds: int) -> str:
    min, sec = divmod(seconds, 60)
    return '%02d.%02d' % (min, sec)

def get_length(text:str):
    return len(re.findall('(?!^\.)([^\.]\.|[^\.]|\.)', text))
    
def split_text(text:str):
    return re.findall('([^\.]\.|[^\.]|\.)', text)

def get_max_length(words:list):
    max = get_length(words[0])
    for i in words:
        if get_length(i) > max:
            max = get_length(i)
    return max

def fit_text(text:str) -> str:
    length = get_length(text)
    if length <= 5 and ' ' not in text:
        return spread_text(text)
    elif length > 12:
        return shorten_text(text)
    return text

def spread_text(text:str) -> str:
    if get_length(text) <= 5  and ' ' not in text:
        text = re.findall('([^\.]\.|[^\.]|\.)', text)
        return ' '.join(text)
    return text
    
def shorten_text(text:str, ignorables:list=['la','de']):
    text = text.strip()
    text = re.sub('\s{2,}',' ',text)
    length = get_length(text)
    if (length <= 12): return text
    words = text.split()
    nb_words = len(words)
    surplus = length - 12
    if nb_words > 1:
        if nb_words > 4:
            words = words[0:4]
            nb_words = 4
            text = ' '.join(words)
            length = get_length(text)
            surplus = length - 12
        while surplus > 0:
            max = get_max_length(words)
            for i in range(len(words)):
                length = get_length(words[i])
                if length <= 2:
                    continue
                if length >= max:
                    splitted = split_text(words[i])
                    splitted.pop()
                    words[i] = ''.join(splitted)
                    if re.search('\.$',words[i]) is None:
                        words[i] += '.'
                    surplus = surplus -1
                    break
        return ' '.join(words)
                    
    splitted = split_text(text)
    return ''.join(splitted[0:12])