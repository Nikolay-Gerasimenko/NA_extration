import pandas as pd
import re
import json

with open('codes_regexp_patterns.json', 'r', encoding='utf-8') as f:
    codes_regexp_patterns = json.load(f)
with open('na_levels_regexp_patterns.json', 'r', encoding='utf-8') as f:
    na_levels_regexp_patterns = json.load(f)

class Codecs:
    def __init__(self, codecs_string):
        if codecs_string is not None:
            for code_type in codes_regexp_patterns:
                if re.match(code_type, codecs_string):
                    self.__code_type = code_type
                    break
        else:
            self.__code_type = None
    
    @property
    def code_type(self):
        return self.__code_type

class NA:
    def __init__(
                    self,
                    codecs = None,
                    glava = None,
                    razdel = None,
                    podrazdel = None,
                    artical = None,
                    chast = None,
                    punct = None,
                    podpunct = None,
                    abzats = None
                 ):
            self.na_levels = {
                                'Code'        :    Codecs(codecs),
                                'CodeChapter' :    glava,
                                'Article'     :    artical,
                                'ArticlePart' :    chast,
                                'Section'     :    punct,
                                'SubSection'  :    podpunct,
                                'Paragraph'   :    abzats,
                              }
            
    def get_info(self):
        res = { na_level:self.na_levels[na_level] for na_level in self.na_levels if self.na_levels[na_level] is not None }
        res['Code'] = res['Code'].code_type
        return res
    
    def __key(self):
        return tuple(v for k, v in sorted(self.get_info().items()))

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __hash__(self):
        return hash(self.__key())
    
class LegalDocument:
    def __init__(self, text):
        self.text = text
        self.__na_list = [na for na_string in self.get_na_strings(text) for na in self.get_na_from_na_string(self.get_marked_na_string(na_string))]
    
    @staticmethod
    def get_na_strings(text, get_pos=False):
        other_simbols = ['-', '\s', ',', 'и', '\.', '\d']
        start_form = '(' + '|'.join(['(' + form + '[' + ''.join(other_simbols) + ']+)' for form in na_levels_regexp_patterns.values()]) + ')+'
        end_form = '(' + '|'.join(['(' + form + ')' for form in codes_regexp_patterns.values()]) + ')'
        na_string_pattern = re.compile(start_form + end_form)
        if get_pos:
            return [(na_string.start(),na_string.end()) for na_string in na_string_pattern.finditer(text)]
        else:
            return [text[na_string.start():na_string.end()] for na_string in na_string_pattern.finditer(text)]
    
    def get_na_from_na_string(self, na_string):
        na_list = []
        
        for na_level in na_levels_regexp_patterns:
            na_level_match = re.match(na_level + '([\d\s\.и]+),?', na_string)
            if(na_level_match != None):
                if len(na_list)==0:
                    includes, na_string = self.get_na_level(na_level, na_string)
                    for include in includes:
                        na = NA()
                        na.na_levels[na_level] = include
                        na_list.append(na)
                else:
                    for na in na_list: na.na_levels[na_level] = na_level_match.group(1).strip()
                    na_string = na_string[na_level_match.end():].strip()
        
        codecs_forms = '(' + '|'.join(['(' + form + ')' for form in codes_regexp_patterns]) + ')'
        codecs = re.match(codecs_forms, na_string)
        if(codecs != None):
            for na in na_list: na.na_levels['Code'] = Codecs(na_string[:codecs.end()].strip())
            return na_list
        
        na_list_from_inside = self.get_na_from_na_string(na_string)
        for na in na_list: na.na_levels['Code'] = na_list_from_inside[0].na_levels['Code']
        na_list += na_list_from_inside
        return na_list

    def get_na_level(self, level_pattern, text):
        na_level_part = re.match(level_pattern + '([\d\s\.,\-и]+)', text)
        dash_numbers = re.search('[\d\.\s]+\-[\d\.\s]+', na_level_part.group(0))
        if dash_numbers is not None:
            na_level_part_without_dash = na_level_part.group(0)[:dash_numbers.start()] + na_level_part.group(0)[dash_numbers.end():]
            ranged_na_levels = re.search('\d+(?=\.)', dash_numbers[0]).group(0)
            punkt_numbers = re.findall('(?<=\.)\d+', dash_numbers[0])
            range_na_levels = [ranged_na_levels + '.{0}'.format(i) for i in range(int(punkt_numbers[0]), int(punkt_numbers[1])+1)]
            na_levels_numbers = re.findall('[\d\.]+', na_level_part_without_dash)
            res = na_levels_numbers + range_na_levels
        else:
            res = re.findall('[\d\.]+', na_level_part.group(0))
        cut_text = text[na_level_part.end():]
        
        return res, cut_text
    
    def get_marked_na_string(self, na_string):
        patterns = {**na_levels_regexp_patterns, **codes_regexp_patterns}
        for na_level in patterns:
            na_string = re.sub(patterns[na_level], na_level, na_string)
        return na_string
    
    def get_na_list(self):
        return self.__na_list
    
    def save_to_json(self, save_path):
        json.dump(self.na_list, open(save_path, 'w'), ensure_ascii=False)
        
    def similarity_score(self, other):
        return len(set(self.__na_list) & set(other.__na_list))
        
    def __eq__(self, other):
        return self.na_list == other.na_list
        
    @property
    def na_list(self):
        return [na.get_info() for na in self.__na_list]
    
    @property 
    def na_set(self):
        return set(self.__na_list)
