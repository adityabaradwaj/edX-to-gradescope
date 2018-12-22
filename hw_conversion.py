import sys
from pprint import pprint
import os
from bs4 import BeautifulSoup
import re
import traceback
from unidecode import unidecode
import mpmath

# For python code form edX
import random

# This is the base folder of the class data.
path_to_class_data = './course/'
path_to_output = "./a/"


def main():
    # v = make_assignment_from_vertical_names(hw0_vertical_names)
    url_name = get_course_url_name()
    chapters = get_course_chapters(url_name)
    for chapter in chapters:
        assignment_title, sequentials = get_sequentials_from_chapter(chapter)
        assignment_title = re.sub("[\\/:\"*?<>|]+", "", assignment_title)
        print(assignment_title)
        assignment_file = open(path_to_output + assignment_title + ".txt", "w")
        for seq in sequentials:
            verticals = get_verticals_from_sequential(seq)
            assignment_data = make_assignment_from_vertical_names(verticals)
            assignment_file.write(assignment_data)
        assignment_file.close()


def get_course_url_name():
    path_to_course_xml = find("course.xml", path_to_class_data)
    if path_to_course_xml is None:
        raise Exception("Could not find the main course xml file!")
    with open(path_to_course_xml) as f:
        soup = BeautifulSoup(f, 'html.parser')
    return soup.find("course")["url_name"]


def get_course_chapters(url_name):
    path_to_course_chapters = find("{}.xml".format(url_name), path_to_class_data)
    if path_to_course_chapters is None:
        raise Exception("Could not find the chapters data!")
    with open(path_to_course_chapters) as f:
        soup = BeautifulSoup(f, 'html.parser')
    return [chapter["url_name"] for chapter in soup.find_all("chapter")]


def get_sequentials_from_chapter(chapter):
    path_to_sequentials = find("{}.xml".format(chapter), path_to_class_data)
    if path_to_sequentials is None:
        raise Exception("Could not find sequential data file!")
    with open(path_to_sequentials) as f:
        soup = BeautifulSoup(f, 'html.parser')
    return soup.find("chapter")["display_name"], [seq["url_name"] for seq in soup.find_all("sequential")]


def get_verticals_from_sequential(sequential):
    path_to_verticals = find("{}.xml".format(sequential), path_to_class_data)
    if path_to_verticals is None:
        raise Exception("Could not find vertical data file!")
    with open(path_to_verticals) as f:
        soup = BeautifulSoup(f, 'html.parser')
    return [vert["url_name"] for vert in soup.find_all("vertical")]

def make_assignment_from_vertical_names(vertical_names):
    output = ""
    for vertical_name in vertical_names:
        path_to_vertical = find('{}.xml'.format(vertical_name), path_to_class_data)
        if path_to_vertical is None:
            raise Exception('Path to vertical is None!')
        with open(path_to_vertical) as f:
            soup = BeautifulSoup(f, 'html.parser')
        
        # vertical_display_name = soup.find_all('vertical')[0]['display_name']
        problem_url_names_and_types = [(tag['url_name'], tag.name) for tag in soup.find_all(['problem', 'html'])]
        for part_index, problem_url_name_and_type in enumerate(problem_url_names_and_types):
            problem_url_name, problem_url_type = problem_url_name_and_type
            if problem_url_type == 'problem':
                path_to_problem = find('{}.xml'.format(problem_url_name), path_to_class_data)
            elif problem_url_type == 'html':
                path_to_problem = find('{}.html'.format(problem_url_name), path_to_class_data)
            else:
                raise Exception('fuck up')
            with open(path_to_problem, encoding="utf8") as f:
                problem_soup = BeautifulSoup(f, 'html.parser')

            for tag in problem_soup.find_all('solution'):
                tag.clear()

            script = problem_soup.find(['script'])
            if script:
                try:
                    exec(format_python_code(script.text), globals())
                except Exception as e:
                    print(e)
                    print(traceback.format_exc())
                    print('ERROR WITH EXECUTING CODE: ', problem_url_name)
            
            tic = TableIndexCounter()
            try:
                problem_text = convert_tag(problem_soup, tic)
            except Exception as e:
                problem_text = None
                print(e)
                print(traceback.format_exc())
                print('ERROR WITH TRANSLATING: ', problem_url_name)
            
            if part_index != 0:
                output += '---------------------\n\n\nPart {}\n'.format(part_index + 1)
                # print('---------------------\n\n')
                # print('Part {}'.format(part_index + 1))
            # print(problem_text)
            if problem_text is not None:
                output += problem_text + "\n"
        output += '\n$$\\phantom{\\rule{0em}{10em}}$$\n___\n\n\n\n' \
                  '--------------------------------------------------------------------\n\n\n'
        # print('\n$$\\phantom{\\rule{0em}{10em}}$$')
        # print('___')
        # print('\n\n\n--------------------------------------------------------------------\n\n\n')
    return output

class TableIndexCounter:
    def __init__(self):
        self.table_index = 0

class TableEntryProcessor:
    def __init__(self, tic):
        self.answers = {}
        self.nested_tables = {}
        self.tic = tic
    
    def process(self, tag):
        table = tag.find('table')
        textline = tag.find('textline')
        if table:
            text = self.process_nested_table(table)
            return text
        elif textline:
            if not textline.has_attr('correct_answer'):
                return ''
            else:
                correct_answer_text, correct_answer_value, points = convert_textline_format(textline)
                self.answers[correct_answer_text] = {
                    'value': correct_answer_value,
                    'points': points,
                }
                return '**' + correct_answer_text + '**'
        else:
            text = re.sub('\$\w+', self.process_match, tag.text)
            text = convert_latex_format(text.strip())
            return text
        
    def process_nested_table(self, table):
        self.nested_tables[self.tic.table_index] = convert_table_format(table, self.tic)
        text = 'Table' + str(self.tic.table_index)
        self.tic.table_index += 1
        return text
        
    def process_match(self, match):
        text = '{' + match.group(0)[1:] + '}'
        text = text.format(**globals())
        try:
            # This still doesn't work
            text = str(float(str(text)))
        except:
            pass
        if '</table>' in text:
            table = BeautifulSoup(text, 'html.parser').find('table')
            text = self.process_nested_table(table)
        return text

def evaluate_variable(match):
    matched_text = match.group(0)[1:]
    text = '{' + matched_text + '}'
    try:
        text = text.format(**globals())
    except KeyError:
        pass
    return text


def evaluate_variables(text):
    return re.sub('\$\w+', evaluate_variable, text)


def convert_latex_format(text):
    return text.replace('\(', '$$').replace('\)', '$$').replace('\[', '$$').replace('\]', '$$').replace('|', ' \mid ')


def convert_img_format(img_src):
    return '![](https://rawgit.com/AdityaB97/cs188/master{})'.format(evaluate_variables(img_src))


def convert_numericalresponse_format(answer):
    return '[____]({})'.format(evaluate_variables(answer))


def convert_choiceresponse_format(tag):
    result = ''
    multichoice = sum([choice['correct'] == 'true' for choice in tag.find_all('choice')]) > 1
    for choice in tag.find_all('choice'):
        if multichoice:
            prefix = '[X] ' if choice['correct'] == 'true' else '[ ] '
        else:
            prefix = '(X) ' if choice['correct'] == 'true' else '( ) '
        result += prefix
        if choice.find('text') is not None:
            result += choice.find('text').text.strip() + '\n'
        else:
            # List comprehension below is a quick fix for HW10 Q6 (actually second question)
            result += ' '.join([str(thing) for thing in choice.contents]) + '\n'
    return result


def convert_textline_format(textline):
    assert textline.has_attr('correct_answer')
    correct_answer_text = re.search('\$\w+', textline['correct_answer'])
    # If the correct answer is a variable, evaluate it. Else, use the raw value
    if correct_answer_text:
        correct_answer_text = correct_answer_text.group(0)[1:]
    else:
        correct_answer_text = textline['correct_answer']
    try:
        correct_answer_value = float(str(eval(correct_answer_text)))
    except Exception as e:
        correct_answer_value = str(eval(correct_answer_text))
    # points = textline['points']
    # Uncomment if points is needed
    points = None
    # Capitalize Answer to make it look better
    correct_answer_text = correct_answer_text.capitalize()
    
    return correct_answer_text, correct_answer_value, points
    

def convert_table_format(table, tic):
    tep = TableEntryProcessor(tic)
    output_string = ''
    
    if table.find('tbody'):
            table = table.find('tbody')
            
    for tag in table.contents:
        if tag.name == 'tr':
            # Hacky solution for tables within tables
            # Removed because this skips tables in variables, like in HW6 Q1
            # if tag.find('table'):
            #     continue
            
            th_tags = tag.find_all('th', recursive=False)
            td_tags = tag.find_all('td', recursive=False)

            # Removed temporarily because this fails when there are nested tables
            # But then resolved the issue by making recursive=False above 
            assert (len(th_tags) > 0) ^ (len(td_tags) > 0), (th_tags, td_tags)

            if len(th_tags) > 0:
                output_string += '| ' + ' '.join([tep.process(th_tag) + ' |' for th_tag in th_tags]) + '\n'
                output_string += '| ' + ' --- |' * len(th_tags) + '\n'
            elif len(td_tags) > 0:
                output_string += '| ' + ' '.join([tep.process(td_tag) + ' |' for td_tag in td_tags]) + '\n'
                
    output_string += '\n$$\\phantom{\\rule{0em}{1em}}$$'
    output_string += '\n\n'
    if len(tep.answers) > 0:
        output_string += '### Input Answers Here \n'
    for answer_name, answer_dict in sorted(tep.answers.items(), key=lambda x : x[0]):
        value, points = answer_dict['value'], answer_dict['points']
        output_string += '**' + answer_name + ':**' + '\n'
        output_string += '[____]({})'.format(value) + '\n\n'
        
    for index, table in sorted(tep.nested_tables.items(), key=lambda x : x[0]):
        output_string += '**Table' + str(index) + ':**' + '\n\n'
        output_string += table + '\n\n'
        
    return output_string

def convert_tag(tag, tic):
    if tag.name == 'table':
        text = convert_table_format(tag, tic)
        text += '\n\n'
        return text
    elif tag.name is None:
        tag_text = str(unidecode(tag)).strip()
        tag_text_evaluated = evaluate_variables(tag_text)
        if tag_text != tag_text_evaluated:
            return convert_tag(BeautifulSoup(tag_text_evaluated, 'html.parser'), tic) + '\n\n'
        else:
            return convert_latex_format(tag_text) + '\n\n'
    elif tag.name == 'problem':
        if tag.has_attr('weight'):
            weight = tag['weight']
        else:
            weight = 1
        try:
            text = tag['display_name'] + ' ' + str(weight)
            text += '\n\n'
        except Exception:
            text = ""
    elif tag.name == 'img':
        text = convert_img_format(tag['src'])
        text += '\n\n'
    elif tag.name == 'numericalresponse' or tag.name == 'stringresponse':
        text = convert_numericalresponse_format(tag['answer'])
        text += '\n\n'
    elif tag.name == 'choiceresponse' or tag.name == 'multiplechoiceresponse':
        text = convert_latex_format(convert_choiceresponse_format(tag))
        text += '\n\n'
        return text
    elif tag.name == 'textline':
        if not tag.has_attr('correct_answer'):
            text = ''
        else:
            correct_answer_text, correct_answer_value, points = convert_textline_format(tag)
            text = '**' + correct_answer_text + ':**' + '\n'
            text += '[____]({})'.format(correct_answer_value)
            text += '\n\n'
    elif (tag.has_attr('type') and tag['type'] == 'loncapa/python') or tag.name in ['style']:
        return ''
    else:
        text = ''
        
    return text + ''.join([convert_tag(child, tic) for child in tag.children if child != '\n'])

def find(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)
        
def format_python_code(text):
    return text.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&').replace("\t", "    ")

if __name__ == '__main__':
    main()