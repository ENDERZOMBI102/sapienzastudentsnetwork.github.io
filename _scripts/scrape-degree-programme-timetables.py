import os
import json
import re
from datetime import datetime
from requests import get
from bs4 import BeautifulSoup


def extract_course_code(course_name):
    # Extract the ID that starts with "AAF" followed by numbers or just a numeric ID
    match = re.match(r"(AAF\d+|\d+)", course_name)
    if not match:
        return None
    id_number = match.group(1)

    # Search for the unit or module number
    roman_to_int = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5}
    unit_number = None
    if "UNIT" in course_name:
        match = re.search(r"UNIT\s*(\d+)", course_name)
        if match:
            # e.g. "UNIT 1" -> "1"
            unit_number = match.group(1)
        else:
            match = re.search(r"UNIT\s*\b(\w+)", course_name)
            if match:
                # Convert Roman numerals to Arabic numbers, if necessary
                # e.g. "UNIT I" -> "1"
                unit_number = str(roman_to_int.get(match.group(1), match.group(1)))
    elif "MODULO" in course_name:
        match = re.search(r"\b(\w+)\s*MODULO", course_name)
        if match:
            # Convert Roman numerals to Arabic numbers, if necessary
            # e.g. "I MODULO" -> "1"
            unit_number = str(roman_to_int.get(match.group(1), match.group(1)))

    # If unit/module number is found, return with underscore; otherwise, just return the ID
    if unit_number:
        return f"{id_number}_{unit_number}"
    else:
        return id_number

def parse(DOM):
    # Iterate through the tables and extract class timetables
    for div in DOM.find_all(class_='sommario'):
        h2_tag_text = div.find('h2').text

        if f"{semester} semestre" not in h2_tag_text:
           continue 

        # Hard-coded list of (course_code, channel, teacher_name) erroneous combinations to be ignored
        ignore_conditions = [
            # ("1015883", "1", "MASI IACOPO"),  # Ignore MASI IACOPO's class for course 1015883 on channel 1
            # ("1020420", "1", "PIPERNO ADOLFO")  # Ignore PIPERNO ADOLFO's class for course 1020420 on channel 1
        ]

        for h3 in div.find_all('h3'):
            # The h3 elements contain text in this format:
            # Canale <Unico/1/2/...>
            channel = h3.text.split()[-1] if h3.text.split()[-1] != "Unico" else '0'

            # The tables are expected to be organized in the following way:
            # Course and teacher info | Building and classroom info | Schedule
            # e.g.
            #      [0]
            #      101226 CALCOLO DIFFERENZIALE
            #         MARIO ROSSI
            #
            #      [1]
            #      Edificio: CU006
            #      Aula III
            #
            #      [2]
            #      lunedì dalle 08:00 alle 11:00
            #      venerdì dalle 08:00 alle 10:00

            for tr in h3.findNext().find_all('tr')[1:]:
                (course_column, classroom_column, schedule_column) = tuple(tr.find_all('td'))
                
                # Find the <a> element containing the course's code
                course_code_link = course_column.find('a')

                # Extract the course code from the course name
                course_name = course_code_link.text
                course_code = extract_course_code(course_name)

                # Prepare to extract teacher data
                teacher_name     = None
                teacher_page_url = None

                # Find the <a> element containing the teacher's name
                teacher_div = course_column.find('div', class_='docente')

                if teacher_div:
                    teacher_a = teacher_div.find('a')

                    # Extract the teacher's name
                    teacher_name = teacher_a.text.strip()

                    # Check if the current combination of course_code, channel, and teacher_name should be ignored
                    if (course_code, channel, teacher_name) in ignore_conditions:
                        continue  # Skip processing if the condition matches

                    # Extract the URL of the teacher's page
                    teacher_page_url = teacher_a['href']

                    # Extract the teacher's UID from the URL of the teacher's page
                    teacher_id = teacher_page_url.split('=')[-1]

                    if teacher_id not in teachers_dict:
                        teachers_dict[teacher_id] = {
                            "name": teacher_name,
                        }
                    else:
                        teachers_dict[teacher_id]["name"] = teacher_name
                else:
                    teacher_id = None

                # Extract location information from column 1 of the table
                location = classroom_column

                # Search for matches for building and classroom in the location string
                building_match = re.search(r'Edificio: (\w+)', str(location), re.IGNORECASE)
                classroom_match = re.search(r'Aula ([\w\s\d]+)', str(location), re.IGNORECASE)

                # If matches for building and classroom are found
                if building_match and classroom_match:
                    # Extract the building name and remove extra spaces
                    building = building_match.group(1)
                    building = re.sub(r'\s+', ' ', building).strip()

                    # Extract the classroom name and remove extra spaces
                    classroom = classroom_match.group(1)
                    classroom = re.sub(r'\s+', ' ', classroom).strip()

                    # Create a new location string that combines building and classroom
                    location = f"Aula {classroom} (Edificio: {building})"
                else:
                    # If no matches are found, use the original text of the location
                    location = location.get_text()

                # Extract the classroom ID from the URL in the 'a' element in column 1
                classroom_id = classroom_column.find('a').get('href').replace("#aula_", "")

                # Extract class timings from the third column
                day_and_time_strings = str(schedule_column).replace("dalle ", "").replace("alle ", "").replace(":00", "")

                for day_and_time_string in day_and_time_strings.replace("<td> ", "").replace("</td>", "").split("<br/>"):
                    # e.g. lunedì dalle 08:00 alle 11:00
                    day_and_time_string_fields = day_and_time_string.split(" ")

                    schedule_day_name   = day_and_time_string_fields[0]
                    schedule_start_time = day_and_time_string_fields[1]
                    schedule_end_time   = day_and_time_string_fields[2]
                    schedule_time_slot  = f"{schedule_start_time} - {schedule_end_time}"
                    schedule_time_slot  = re.sub(r'\b0(\d)', r'\1', schedule_time_slot)

                    # 1055043 - STATISTICS is offered in both ACSAI and Cybersecurity, but with different professors and schedules
                    if course_code == "1055043" and os.getenv("DEGREE_PROGRAMME_CODE", "29923") == "29389":
                        course_code = "1055043_2"

                    if course_code not in course_timetables_dict:
                        course_timetables_dict[course_code] = {
                            "subject": ' '.join(course_column.find('a').text.split()[1:]),
                            "degree": degree_programme_code,
                            "channels": {},
                            "code": course_column.find(class_='codiceInsegnamento').text
                        }

                        # 1047622 - Cryptography
                        # 10589555 - Practical Network Defense
                        if course_code in ("1047622", "10589555"):
                            course_timetables_dict[course_code]["degree"] = "29389"

                    if f"{channel}" not in course_timetables_dict[course_code]["channels"]:
                        course_timetables_dict[course_code]["channels"][f"{channel}"] = {}

                    if schedule_day_name not in course_timetables_dict[course_code]["channels"][f"{channel}"]:
                        # Create a new dictionary for the day name with class information for the channel
                        course_timetables_dict[course_code]["channels"][f"{channel}"][schedule_day_name] = [{
                            "teacher": teacher_id,
                            "timeslot": schedule_time_slot,
                            "classrooms": {
                                classroom_id: location
                            }
                        }]
                    else:
                        # If the same schedule is already present, add the location to the list of classrooms
                        #
                        # Useful for courses that are held, by the same teacher,
                        # in more than one classroom at the same time slot (usually
                        # those in laboratories)
                        #

                        append_schedule = True

                        for day_schedule_entry_dict in course_timetables_dict[course_code]["channels"][f"{channel}"][schedule_day_name]:
                            if (day_schedule_entry_dict["teacher"] == teacher_id) and (day_schedule_entry_dict["timeslot"] == schedule_time_slot):
                                day_schedule_entry_dict["classrooms"][classroom_id] = location
                                append_schedule = False
                                break
                        
                        if append_schedule:
                            course_timetables_dict[course_code]["channels"][f"{channel}"][schedule_day_name].append({
                                "teacher": teacher_id,
                                "timeslot": schedule_time_slot,
                                "classrooms": {
                                    classroom_id: location
                                }
                            })

    # Sort days
    sort_days_order = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì"]

    for course_code, course_code_data in course_timetables_dict.items():
        sorted_channels = {}

        for channel, day_data in course_code_data["channels"].items():
            sorted_days = {day: day_data[day] for day in sort_days_order if day in day_data}
            sorted_channels[channel] = sorted_days

        course_timetables_dict[course_code]["channels"] = sorted_channels

    #  ▀▀█▀▀ ▀█▀ ▒█▀▄▀█ ▒█▀▀▀ ▀▀█▀▀ ░█▀▀█ ▒█▀▀█ ▒█░░░ ▒█▀▀▀ ▒█▀▀▀█ ░░ ▒█▀▀█ ░█▀▀█ ▒█░░▒█
    #  ░▒█░░ ▒█░ ▒█▒█▒█ ▒█▀▀▀ ░▒█░░ ▒█▄▄█ ▒█▀▀▄ ▒█░░░ ▒█▀▀▀ ░▀▀▀▄▄ ▀▀ ▒█▄▄▀ ▒█▄▄█ ▒█▒█▒█
    #  ░▒█░░ ▄█▄ ▒█░░▒█ ▒█▄▄▄ ░▒█░░ ▒█░▒█ ▒█▄▄█ ▒█▄▄█ ▒█▄▄▄ ▒█▄▄▄█ ░░ ▒█░▒█ ▒█░▒█ ▒█▄▀▄█

    data = []

    for div in DOM.find_all(class_='sommario'):
        year = {
            'year': div.find('h2').text,
            'channels': []
        }

        for h3 in div.find_all('h3'):
            channel = {
                'channel': h3.text,
                'timetable': []
            }

            for tr in h3.findNext().find_all('tr')[1:]:
                (course, room, schedule) = tuple(tr.find_all('td'))

                section = {
                    'course': course.find(class_='codiceInsegnamento').text,
                    'subject': ' '.join(course.find('a').text.split()[1:]),
                    'building': room.find('div').text,
                    'room': room.find('a').text,
                    'teacher': (course.find(class_='docente') or DOM.new_tag('p')).text,
                    'schedule': []
                }

                for day_time in filter(lambda x: x.name != 'br', schedule.contents):
                    (day, _, from_, _, to) = day_time.split()

                    section['schedule'].append({
                        'day': day,
                        'from': from_,
                        'to': to
                    })

                channel['timetable'].append(section)

            year['channels'].append(channel)

        data.append(year)

    # ▒█▀▀█ ▒█░░░ ░█▀▀█ ▒█▀▀▀█ ▒█▀▀▀█ ▒█▀▀█ ▒█▀▀▀█ ▒█▀▀▀█ ▒█▀▄▀█ ▒█▀▀▀█ ░ ░░░▒█ ▒█▀▀▀█ ▒█▀▀▀█ ▒█▄░▒█
    # ▒█░░░ ▒█░░░ ▒█▄▄█ ░▀▀▀▄▄ ░▀▀▀▄▄ ▒█▄▄▀ ▒█░░▒█ ▒█░░▒█ ▒█▒█▒█ ░▀▀▀▄▄ ▄ ░▄░▒█ ░▀▀▀▄▄ ▒█░░▒█ ▒█▒█▒█
    # ▒█▄▄█ ▒█▄▄█ ▒█░▒█ ▒█▄▄▄█ ▒█▄▄▄█ ▒█░▒█ ▒█▄▄▄█ ▒█▄▄▄█ ▒█░░▒█ ▒█▄▄▄█ █ ▒█▄▄█ ▒█▄▄▄█ ▒█▄▄▄█ ▒█░░▀█

    # Get all the rows in the classrooms table except the first one (header)
    rows = DOM.find(class_='elenco_aule').find_all('tr')[1:]

    # Iterate through the table rows to extract classroom information
    # The tables is expected to be organized in the following way:
    # Brief description of the classroom | Classroom address info
    # e.g.
    #      [0]
    #      Aula 1 - Aule L Via del Castro Laurenziano 7a
    #
    #      [1]
    #      VIA del Castro Laurenziano, 7a ROMA presso Aule L Via del Castro Laurenziano 7a, Provincia di Roma mappa

    for row in rows:
        # Find the <a> tag within the row
        a_tag = row.find('a')

        if a_tag:
            # Extract the 'name' attribute and remove the 'aula_' prefix to get the classroom ID
            id = a_tag.get('name').replace('aula_', '')
            
            # Extract the classroom description and address, removing superfluous and/or repeated information
            td_tags = row.find_all('td')
            raw_description = td_tags[0].text
            description = raw_description.strip().split(" - Aule - Via")[0].split(" Via")[0]

            address = td_tags[1].text.strip().split(" ROMA ")[0]
            if "presso" in address:
                address = None
            
            # Change the first word so that only its first letter is capitalized
            # e.g. VIA del Castro Laurenziano, 7a -> Via del Castro Laurenziano, 7a
            address = (address.split()[0].capitalize() + ' ' + ' '.join(address.split()[1:])) if address else None

            # Default to "Viale Regina Elena, 295" as address for classrooms
            # having ' - Regina Elena - ' in description but no valid address
            # 
            # e.g. Denominazione: AULA 101 - Regina Elena - Edificio D
            #      Indirizzo: , presso Regina Elena - Edificio D, Provincia di Roma
            #      ->
            #      description: AULA 101 - Regina Elena - Edificio D
            #      address: null
            #      ->
            #      address: Viale Regina Elena, 295
            if " - Regina Elena - " in description and address is None:
                address = "Viale Regina Elena, 295"

            # Use a regular expression to replace multiple spaces with a single space
            if description:
                description = re.sub(r'\s+', ' ', description)

            if address:
                address = re.sub(r'\s+', ' ', address)
            
            # Extract the map link from the 'href' property of the 'a' element within the 'Address' cell
            map_a_tag = td_tags[1].find('a')

            if map_a_tag:
                map_link = map_a_tag.get('href')
            elif "Aule temporanee Via De Lollis" in raw_description:
                map_link = "https://maps.app.goo.gl/gxUJ8cNbmBPtiHcd9"
            else:
                map_link = None
            
            # Create an information dictionary for this classroom
            classrooms_dict[id] = {
                "description": description,
                "address": address,
                "mapsUrl": map_link
            }

    return data


def load_dict_from_json(source_file_name):
    if os.path.exists(source_file_name):
        try:
            # Try to open the file as JSON
            with open(source_file_name, "r") as file:
                dictionary_data = json.load(file)

                print(f"File '{source_file_name}' opened successfully and loaded as a dictionary.")

                return dictionary_data

        except json.JSONDecodeError:
            # If the file is not a valid JSON, rename the file by adding the .bak extension
            # with the current date and time to avoid overwriting it when it might not be desired
            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            new_file_name = f"{source_file_name}.bak{current_time}"
            os.rename(source_file_name, new_file_name)

            print(f"The file '{source_file_name}' is not a valid JSON, renamed to '{new_file_name}'.")
    else:
        print(f"File '{source_file_name}' not found.")

    return {}


if __name__ == '__main__':
    # ▒█▀▀▀█ ▒█▀▀█ ▀▀█▀▀ ▀█▀ ▒█▀▀▀█ ▒█▄░▒█ ▒█▀▀▀█ 
    # ▒█░░▒█ ▒█▄▄█ ░▒█░░ ▒█░ ▒█░░▒█ ▒█▒█▒█ ░▀▀▀▄▄ 
    # ▒█▄▄▄█ ▒█░░░ ░▒█░░ ▄█▄ ▒█▄▄▄█ ▒█░░▀█ ▒█▄▄▄█

    # Semester to scrape lesson timetables for
    semester = os.getenv("SEMESTER", "primo")

    # Degree program to scrape data for
    degree_programme_code = os.getenv("DEGREE_PROGRAMME_CODE", "29923")

    # Academic Year of the degree program to scrape data for
    academic_year = os.getenv("ACADEMIC_YEAR", "2024/2025")

    # Url of the gomppublic page containing timetables and classrooms for the specific degree program
    gomppublic_generateorario_url = os.getenv("GOMPPUBLIC_GENERATEORARIO_URL", 'https://gomppublic.uniroma1.it/ScriptService/OffertaFormativa/Ofs.6.0/AuleOrariScriptService/GenerateOrario.aspx?params={"controlID":"","aulaUrl":"","codiceInterno":{codiceInterno},"annoAccademico":"{annoAccademico}","virtuale":false,"timeSlots":null,"displayMode":"Manifesto","showStyles":false,"codiceAulaTagName":"","nomeAulaCssClass":"","navigateUrlInsegnamentoMode":"","navigateUrlInsegnamento":"","navigateUrlDocenteMode":"","navigateUrlDocente":"","repeatTrClass":""}&_=1702740827520')\
        .replace("{codiceInterno}", degree_programme_code)\
        .replace("{annoAccademico}", academic_year)

    # File to read and write classroom data to
    classrooms_file_name = "../data/classrooms.json"

    # File to read and write teacher data to
    teachers_file_name = "../data/teachers.json"

    # File to read and write course timetables info to
    course_timetables_file_name = "../data/timetables.json"

    #
    # ▒█░░░ ▒█▀▀▀█ ░█▀▀█ ▒█▀▀▄ 　 ▒█▀▀▄ ░█▀▀█ ▀▀█▀▀ ░█▀▀█
    # ▒█░░░ ▒█░░▒█ ▒█▄▄█ ▒█░▒█ 　 ▒█░▒█ ▒█▄▄█ ░▒█░░ ▒█▄▄█
    # ▒█▄▄█ ▒█▄▄▄█ ▒█░▒█ ▒█▄▄▀ 　 ▒█▄▄▀ ▒█░▒█ ░▒█░░ ▒█░▒█
    #

    # Dictionary to store classroom information
    classrooms_dict = load_dict_from_json(classrooms_file_name)

    # Dictionary to store teacher info
    teachers_dict = load_dict_from_json(teachers_file_name)

    # Dictionary to store course timetables
    course_timetables_dict = load_dict_from_json(course_timetables_file_name)

    #
    # ▒█▀▀▀█ ▒█▀▀█ ▒█▀▀█ ░█▀▀█ ▒█▀▀█ ▒█▀▀▀ 　 ▒█▀▀▄ ░█▀▀█ ▀▀█▀▀ ░█▀▀█
    # ░▀▀▀▄▄ ▒█░░░ ▒█▄▄▀ ▒█▄▄█ ▒█▄▄█ ▒█▀▀▀ 　 ▒█░▒█ ▒█▄▄█ ░▒█░░ ▒█▄▄█
    # ▒█▄▄▄█ ▒█▄▄█ ▒█░▒█ ▒█░▒█ ▒█░░░ ▒█▄▄▄ 　 ▒█▄▄▀ ▒█░▒█ ░▒█░░ ▒█░▒█
    #

    DOM = BeautifulSoup(
        ' '.join(get(gomppublic_generateorario_url).content[13:-3].decode('unicode-escape').split()),
        'html.parser'
    )

    #
    # ▒█▀▀▀ ▀▄▒▄▀ ▒█▀▀█ ▒█▀▀▀█ ▒█▀▀█ ▀▀█▀▀ 　 ▒█▀▀▄ ░█▀▀█ ▀▀█▀▀ ░█▀▀█
    # ▒█▀▀▀ ░▒█░░ ▒█▄▄█ ▒█░░▒█ ▒█▄▄▀ ░▒█░░ 　 ▒█░▒█ ▒█▄▄█ ░▒█░░ ▒█▄▄█
    # ▒█▄▄▄ ▄▀▒▀▄ ▒█░░░ ▒█▄▄▄█ ▒█░▒█ ░▒█░░ 　 ▒█▄▄▀ ▒█░▒█ ░▒█░░ ▒█░▒█
    #

    # This function takes a Python dictionary, converts it to a JSON-formatted
    # string, escapes double quote characters within the JSON string, and then
    # parses the modified JSON string back into a Python dictionary

    def escape_dict_double_quotes(input_dict) -> dict:
        # Convert the input dictionary to a JSON-formatted string with 4-space indentation
        input_dict_json_string = json.dumps(input_dict, indent=4)

        # Use a regular expression to replace double quote characters within the JSON string
        # with escaped double quotes if they are not already escaped (not preceded by a backslash)
        input_dict_json_string = re.sub(r'(?<!\\)\\"', r'\\\\\\"', input_dict_json_string)

        # Return the resulting dictionary after parsing the JSON string
        return json.loads(input_dict_json_string)

    # Save the timetables to a JSON file
    with open(f"../data/timetables_raw_{degree_programme_code}_{academic_year.replace('/', '-')}.json", 'w') as rawTimetablesFile:
        json.dump(parse(DOM), rawTimetablesFile, indent=2)

    # ▀▀█▀▀ █▀▀ █▀▄▀█ █▀▀█ █▀▀█ █▀▀█ █▀▀█ █▀▀█ █░░█ 　 ▀▀█▀▀ ░▀░ █▀▄▀█ █▀▀ ▀▀█▀▀ █▀▀█ █▀▀▄ █░░ █▀▀ █▀▀
    # ░░█░░ █▀▀ █░▀░█ █░░█ █░░█ █▄▄▀ █▄▄█ █▄▄▀ █▄▄█ 　 ░░█░░ ▀█▀ █░▀░█ █▀▀ ░░█░░ █▄▄█ █▀▀▄ █░░ █▀▀ ▀▀█
    # ░░▀░░ ▀▀▀ ▀░░░▀ █▀▀▀ ▀▀▀▀ ▀░▀▀ ▀░░▀ ▀░▀▀ ▄▄▄█ 　 ░░▀░░ ▀▀▀ ▀░░░▀ ▀▀▀ ░░▀░░ ▀░░▀ ▀▀▀░ ▀▀▀ ▀▀▀ ▀▀▀

    currentDate = datetime.now()

    zoom_register_it = "Zoom (registrarsi tramite questo link)"
    zoom_register_en = "Zoom (register using this link)"

    zoom_login_it = "Zoom (effettuare l'accesso tramite account Sapienza)"
    zoom_login_en = "Zoom (login with Sapienza account)"

    scienzebiochimiche_aulaA = "Aula A Scienze Biochimiche (CU010)"
    scienzebiochimiche = "https://maps.app.goo.gl/FDurWQ4cwoQVqCn5A"

    reginaelena_edificiod_aula_101 = "Aula 101 Regina Elena Ed. D (RM112)"
    reginaelena_edificiod_aula_201 = "Aula 201 Regina Elena Ed. D (RM112)"
    reginaelena_edificiod_aula_301 = "Aula 301 Regina Elena Ed. D (RM112)"
    reginaelena_edificiod = "https://maps.app.goo.gl/7MAGdzdLAbU3Tae7A"

    matematica_aula_iv = "Aula IV Matematica G. Castelnuovo (CU006)"
    matematica_aula_v  = "Aula V Matematica G. Castelnuovo (CU006)"
    matematica_building = "https://maps.app.goo.gl/oU37nArvFccRYNvQ7"

    clinica_odontoiatrica_aula_a1 = 'Aula A1 Luigi Capozzi Via Caserta, 6'
    clinica_odontoiatrica_aula_a2 = 'Aula A2 Luigi Capozzi Via Caserta, 6'
    clinica_odontoiatrica = "https://maps.app.goo.gl/TwTzZBTvbskzgjPNA"

    viascarpa_classroom_id   = "1e079880-d2d2-49ef-8058-c58ab0baa4b4"
    viascarpa_classroom_desc = "Aula 11 (Edificio: RM005)"

    aula_1l_classroom_id   = "3247d3bb-417e-4bba-8e7e-829bbb3863de"
    aula_1l_classroom_desc = "Aula 1 (Edificio: RM018)"

    aula_2l_classroom_id   = "625390f2-0bbb-4072-b866-50902fa1bad9"
    aula_2l_classroom_desc = "Aula 2 (Edificio: RM018)"

    first_year_informatica_teachings = set(["101226", "1015883", "1020420", "1015880"])
    second_year_informatica_teachings = set(["1015886", "1015887_1", "1020421", "1020422_1"])
    first_and_second_year_informatica_teachings = first_year_informatica_teachings | second_year_informatica_teachings

    first_year_acsai_teachings = set(["10595099_1", "10595546_1", "10595524", "10595102_1", "10595102_2"])
    second_year_acsai_teachings = set(["10595529", "10595617_1", "10595525", "10595616_1", "10595616_2"])
    first_and_second_year_acsai_teachings = first_year_acsai_teachings | second_year_acsai_teachings

    if degree_programme_code == "29923":
        # 1020421 - CALCOLO DELLE PROBABILITÀ - Prof.ssa Faggionato
        # Nuovo assetto orario in "vigore dalla data
        # odierna, 15/10/2024, fino a fine semestre"
        #
        # La lezione del martedì di CALCOLO DELLE PROBABILITA' è stata spostata
        # al venerdì, in Aula 11, Via Scarpa, dalle ore 12.00 alle ore 14.00.
        if "martedì" in course_timetables_dict["1020421"]["channels"]["2"]:
            course_timetables_dict["1020421"]["channels"]["2"].pop("martedì")

        if "venerdì" not in course_timetables_dict["1020421"]["channels"]["2"]:
            course_timetables_dict["1020421"]["channels"]["2"]["venerdì"] = [
                {
                    "teacher": "ba1d4b3b-ce47-411a-9bf9-af7ecf4be784",
                    "timeslot": "12 - 14",
                    "classrooms": {
                      "1e079880-d2d2-49ef-8058-c58ab0baa4b4": "Aula 11 (Edificio: RM005)"
                    }
                }
            ]

        # 1020422_1 - SISTEMI OPERATIVI I - Prof. De Gaspari
        # Nuovo assetto orario in "vigore dalla data
        # odierna, 15/10/2024, fino a fine semestre"
        #
        # La lezione del martedì di SISTEMI OPERATIVI è stata
        # spostata in Aula 1L. L'orario resta invariato.
        if "2" not in course_timetables_dict["1020422_1"]["channels"]:
            course_timetables_dict["1020422_1"]["channels"]["2"] = {}

        if "martedì" not in course_timetables_dict["1020422_1"]["channels"]["2"]:
            course_timetables_dict["1020422_1"]["channels"]["2"]["martedì"] = [
              {
                "teacher": "e9de79a3-2dfd-4d7c-a56e-426fb60f5a66",
                "timeslot": "15 - 17",
                "classrooms": {
                  aula_1l_classroom_id: aula_1l_classroom_desc
                }
              }
            ]

        # La lezione del venerdì di SISTEMI OPERATIVI è stata
        # posticipata di un'ora: dalle 14.00 alle 17.00.
        if "venerdì" not in course_timetables_dict["1020422_1"]["channels"]["2"]:
            course_timetables_dict["1020422_1"]["channels"]["2"]["venerdì"] = [
              {
                "teacher": "e9de79a3-2dfd-4d7c-a56e-426fb60f5a66",
                "timeslot": "14 - 17",
                "classrooms": {
                  "1e079880-d2d2-49ef-8058-c58ab0baa4b4": "Aula 11 (Edificio: RM005)"
                }
              }
            ]

        # 10596283 - ORGANIZZAZIONE E GESTIONE PER LO START-UP AZIENDALE
        # Prof. Michelangelo Smeriglio:
        # "
        # Visto che l'aula T1 è un po' piccola (venerdì scorso era tutta piena)
        # sono riuscito ad ottenere l'utilizzo dell'aula magna anche per la lezione
        # del venerdì. Pertanto a partire dal 25/10/2024 il corso si terrà nell'aula
        # magna per entrambi i nostri appuntamenti
        # "
        if "venerdì" not in course_timetables_dict["10596283"]["channels"]["0"]:
            course_timetables_dict["10596283"]["channels"]["0"]["venerdì"] = [
              {
                "teacher": "17631fe6-2af6-407a-a425-cbdc7c9f3bdd",
                "timeslot": "13 - 15",
                "classrooms": {
                  "74a8a956-ade6-4883-b10f-416c38c9d93d": "Aula Magna (Edificio: RM111)"
                }
              }
            ]

    elif degree_programme_code == "29932":
        # 10589621 - ADVANCED MACHINE LEARNING
        course_timetables_dict["10589621"]["channels"]["0"].pop("giovedì")

        # 10600495 - AUTOMATIC VERIFICATION OF INTELLIGENT SYSTEMS
        course_timetables_dict["10600495"]["channels"]["0"]["lunedì"] = [
          {
            "teacher": "2bf66397-ce7b-43e0-b640-ca1e45805df4",
            "timeslot": "14 - 16",
            "classrooms": {
              "3204f38e-7393-4457-a108-c048458d026a": "Aula S1 (Edificio: RM113)"
            }
          }
        ]

        # 1047627 - FOUNDATIONS OF DATA SCIENCE
        course_timetables_dict["1047627"] = {
            "subject": "FOUNDATIONS OF DATA SCIENCE",
            "degree": "29932",
            "channels": {
              "0": {
                "luned\u00ec": [
                  {
                    "teacher": "c6ebe64b-d218-4bed-9643-8de250010478",
                    "timeslot": "10 - 13",
                    "classrooms": {
                      aula_2l_classroom_id : aula_2l_classroom_desc
                    }
                  }
                ],
                "venerd\u00ec": [
                  {
                    "teacher": "c6ebe64b-d218-4bed-9643-8de250010478",
                    "timeslot": "11 - 13",
                    "classrooms": {
                      aula_2l_classroom_id : aula_2l_classroom_desc
                    }
                  }
                ]
              }
            },
            "code": "1047627"
        }

    elif degree_programme_code == "29389":
        # 1047622 - CRYPTOGRAPHY
        if "1047622" in course_timetables_dict and "venerdì" not in course_timetables_dict["1047622"]["channels"]["0"]:
            course_timetables_dict["1047622"]["channels"]["0"]["venerdì"] = [
              {
                "teacher": "0dfd0deb-ac72-429b-8258-3a34436a560c",
                "timeslot": "11 - 13",
                "classrooms": {
                  aula_1l_classroom_id : aula_1l_classroom_desc
                }
              }
            ]

        # 1055043_2 - STATISTICS
        if "1055043_2" in course_timetables_dict and "giovedì" in course_timetables_dict["1055043_2"]["channels"]["0"]:
            course_timetables_dict["1055043_2"]["channels"]["0"]["giovedì"][0]["classrooms"] = {
              aula_2l_classroom_id : aula_2l_classroom_desc
            }

    if currentDate <= datetime(2024, 11, 3):
        for course_code, course_data in course_timetables_dict.items():
            for channel_id, channel_data in course_data["channels"].items():
                if (course_data["degree"] not in ("29932", "29389")) and ("venerdì" in channel_data):
                    channel_data.pop("venerdì")

                for day_name, day_schedules in channel_data.items():
                    for day_schedule in day_schedules:
                        # 101226 - CALCOLO DIFFERENZIALE
                        # L'incarico docenza per il Canale A-L è assegnato al prof. Valeriano Aiello,
                        # non più, alla professoressa Garroni, diventata direttrice a Matematica.
                        if (course_code == "101226") and (channel_id == "1"):
                            if day_schedule["teacher"] == "5374367e-49df-4ff1-985b-ab4b4612e702":
                                day_schedule["teacher"] = None
                                day_schedule["teacherInfo"] = "AIELLO VALERIANO"
                                day_schedule["teacherUrl"] = "https://corsidilaurea.uniroma1.it/it/users/valerianoaiellouniroma1it"

                        if "classrooms" in day_schedule:
                            for classroom_id, classroom_description in day_schedule["classrooms"].items():
                                classroom_info = day_schedule.get("classroomInfo", None)
                                classroom_url  = day_schedule.get("classroomUrl", None)

                                if "(Edificio: RM158)" in classroom_description:
                                    if channel_id == "1":
                                        if course_code in first_and_second_year_informatica_teachings:
                                            classroom_info = clinica_odontoiatrica_aula_a1
                                            classroom_url  = clinica_odontoiatrica

                                    elif channel_id == "2":
                                        if day_name == "martedì":
                                            classroom_info = clinica_odontoiatrica_aula_a1
                                            classroom_url  = clinica_odontoiatrica

                                        elif day_name == "mercoledì":
                                            if course_code == "1020421":
                                                classroom_info = reginaelena_edificiod_aula_301 + " + a distanza (clicca per il link)"
                                                classroom_url  = "https://uniroma1.zoom.us/j/81062850219"

                                                day_schedule["timeslot"] = "11 - 13"

                                            elif course_code in second_year_informatica_teachings:
                                                classroom_info = "Aula I - Chimica \"Vincenzo Caglioti\" (CU032)"
                                                classroom_url  = "https://maps.google.com/maps?q=41.901572,+12.516295+(aula+I)&iwloc=A&hl=it"

                                                #day_schedule["classrooms"] = {
                                                #    "44f829c8-fa6f-4c51-8e6d-6631432d4ab0": "Aula I - Chimica \"Vincenzo Caglioti\" (CU032)"
                                                #}

                                                if course_code == "1020421":
                                                    day_schedule["timeslot"] = "14 - 15"

                                    elif channel_id == "0":
                                        if course_code in first_and_second_year_acsai_teachings:
                                            if day_name in ("lunedì", "giovedì"):
                                                classroom_info = reginaelena_edificiod_aula_301
                                                classroom_url  = reginaelena_edificiod

                                        if course_code in first_year_acsai_teachings:
                                            classroom_info = reginaelena_edificiod_aula_301
                                            classroom_url  = reginaelena_edificiod

                                        elif course_code in second_year_acsai_teachings:
                                            if day_name in ("lunedì", "giovedì"):
                                                classroom_info = reginaelena_edificiod_aula_301
                                                classroom_url  = reginaelena_edificiod

                                            elif day_name == "martedì":
                                                classroom_info = clinica_odontoiatrica_aula_a2
                                                classroom_url  = clinica_odontoiatrica

                                        # INGEGNERIA DEL SOFTWARE - 1022301 - Enrico Tronci
                                        elif course_code == "1022301":
                                            if day_name == "lunedì":
                                                classroom_info = clinica_odontoiatrica_aula_a1
                                                classroom_url  = clinica_odontoiatrica

                                        # AUTOMI CALCOLABILITA' E COMPLESSITA' - 1041727 - Daniele Venturi
                                        #elif course_code == "1041727":
                                        #    if day_name == "venerdì":
                                        #        classroom_info = reginaelena_edificiod_aula_301
                                        #        classroom_url  = reginaelena_edificiod

                                #elif course_code in ("1022267", "10595534"):
                                #    if day_name == "giovedì":
                                #        classroom_info = clinica_odontoiatrica_aula_a2
                                #        classroom_url  = clinica_odontoiatrica

                                if classroom_info is not None:
                                    day_schedule.pop("classrooms")

                                    #print("classroom_info: " + classroom_description + " -> " + classroom_info)

                                    day_schedule["classroomInfo"] = classroom_info
                                #else:
                                #    print("classroom_info: " + classroom_description)

                                if classroom_info == "TBA" and classroom_url is None:
                                    if degree_programme_code == "29923":
                                        classroom_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSZOo9l-8p4dZZzSSjE3S3jV2nEawAlF_fDx4U36ps06ebJseGYnFrTClKs2hLLDuLMzblqm7mLryg1/pubhtml?gid=1994192526&single=true"
                                    elif degree_programme_code == "30786":
                                        classroom_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSZOo9l-8p4dZZzSSjE3S3jV2nEawAlF_fDx4U36ps06ebJseGYnFrTClKs2hLLDuLMzblqm7mLryg1/pubhtml?gid=2076434169&single=true"
                                    elif degree_programme_code == "29932":
                                        classroom_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSZOo9l-8p4dZZzSSjE3S3jV2nEawAlF_fDx4U36ps06ebJseGYnFrTClKs2hLLDuLMzblqm7mLryg1/pubhtml?gid=649156826&single=true"

                                if classroom_url is not None:
                                    day_schedule["classroomUrl"] = classroom_url

    #
    # ▒█▀▀▀ ▀▄▒▄▀ ▒█▀▀█ ▒█▀▀▀█ ▒█▀▀█ ▀▀█▀▀ 　 ▒█▀▀▄ ░█▀▀█ ▀▀█▀▀ ░█▀▀█
    # ▒█▀▀▀ ░▒█░░ ▒█▄▄█ ▒█░░▒█ ▒█▄▄▀ ░▒█░░ 　 ▒█░▒█ ▒█▄▄█ ░▒█░░ ▒█▄▄█
    # ▒█▄▄▄ ▄▀▒▀▄ ▒█░░░ ▒█▄▄▄█ ▒█░▒█ ░▒█░░ 　 ▒█▄▄▀ ▒█░▒█ ░▒█░░ ▒█░▒█
    #

    # Save the classroom information to a JSON file
    with open(f"../data/classrooms.json", 'w') as classroomsFile:
        json.dump(escape_dict_double_quotes(classrooms_dict), classroomsFile, indent=2)

    # Save the teacher information to a JSON file
    with open(f"../data/teachers.json", 'w') as teachersFile:
        json.dump(escape_dict_double_quotes(teachers_dict), teachersFile, indent=2)

    # Save the course timetables to a JSON file
    with open(f"../data/timetables.json", 'w') as timetablesFile:
        json.dump(escape_dict_double_quotes(course_timetables_dict), timetablesFile, indent=2)
