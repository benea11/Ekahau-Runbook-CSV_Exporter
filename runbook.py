from zipfile import ZipFile
import json
import argparse
import math
import csv
import shutil



parser = argparse.ArgumentParser(
    description='Collect vital information from an Ekahau project file and create CSV project run book')
parser.add_argument('file', metavar='esx_file', help='Ekahau project file')

args = parser.parse_args()
file = args.file


def main():
    ekahau_extractor(file)

    with open('project/tagKeys.json') as j:
        tagKeys = json.load(j)

    # Open the required JSON files
    with open('project/floorPlans.json') as j:
        floorplanJSON = json.load(j)

    with open('project/accessPoints.json') as j:
        apJSON = json.load(j)

    with open('project/simulatedRadios.json') as j:
        srJSON = json.load(j)

    with open('project/antennaTypes.json') as j:
        antennaTypes = json.load(j)

    # Load the notes.json file into the notes dictionary
    with open('project/notes.json') as json_file:
        notes = json.load(json_file)

    # Load the cableNotes.json file into the cableNotes dictionary
    with open('project/cableNotes.json') as json_file:
        cableNotes = json.load(json_file)

    jsons = {}
    jsons['tagKeys'] = tagKeys['tagKeys']
    jsons['floorPlan'] = floorplanJSON['floorPlans']
    jsons['ap'] = apJSON['accessPoints']
    jsons['simradio'] = srJSON['simulatedRadios']
    jsons['antenna'] = antennaTypes['antennaTypes']
    jsons['notes'] = notes['notes']
    jsons['cablenotes'] = cableNotes['cableNotes']

    output, error = constructor(jsons)

    if error == True:
        print("SOMETHING WENT WRONG!")
    csvcreate(data=output)
    shutil.rmtree('project')

def csvcreate(data):

    headers = 'AP Name', 'Floor', 'AP Vendor', 'AP Model', 'Ethernet MAC Address', \
              'Antenna Name', 'Antenna Orientation', 'Antenna/AP Height', 'Antenna Tilt', 'Distance to IDF', \
              'IDF Name', 'Patch Panel Number', 'Switch Name', 'Switch Port', 'Status'
    f = open('runbook.csv', 'w')
    with f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for i in data:
            try:
                row = [data[i]['ap name'],
                   data[i]['floor'],
                   data[i]['ap vendor'],
                   data[i]['ap model'],
                   '',
                   data[i]['antennaName'],
                   data[i]['antennaOrientation'],
                   data[i]['antennaHeight'],
                   data[i]['antennaTilt'],
                   data[i]['distancetoIDF'],
                   data[i]['IDF'],
                   '',
                   '',
                   '',
                   '']
                writer.writerow(row)
                error = False
            except:
                error = True


    return error

def ekahau_extractor(file):
    # extract esx to project directory
    with ZipFile(file, 'r') as zip:
        zip.extractall('project')

    return


def constructor(jsons):
    dict = {}
    for ap in jsons['ap']:
        tag_id = ""
        if ap['status'] == "DELETED":
            continue


        dict[ap['id']] = {}
        dict[ap['id']]['ap name'] = ap['name']
        dict[ap['id']]['ap vendor'] = ap['vendor']
        dict[ap['id']]['ap model'] = ap['model'].split(' +')[0]
        dict[ap['id']]['floorplanId'] = ap['location']['floorPlanId']
        dict[ap['id']]['tags'] = ap['tags']
        dict[ap['id']]['location'] = ap['location']['floorPlanId']
        for tag in jsons['tagKeys']:

            if tag['key'] == 'rack':
                for ap_tags in ap['tags']:
                    if ap_tags['tagKeyId'] == tag['id']:
                        dict[ap['id']]['IDF'] = ap_tags['value']
        for floor in jsons['floorPlan']:
            if ap['location']['floorPlanId'] == floor['id']:
                dict[ap['id']]['floor'] = floor['name']
                dict[ap['id']]['mpu'] = floor['metersPerUnit']
        iap = "802i"
        if iap in ap['model']:
            dict[ap['id']]['antenna'] = "Internal"
        for radio in jsons['simradio']:
            if radio['status'] != 'DELETED':
                if ap['id'] == radio['accessPointId']:
                    if radio['accessPointIndex'] == 1:
                        dict[ap['id']]['antennaId'] = radio['antennaTypeId']
                        dict[ap['id']]['antennaTilt'] = radio['antennaTilt']
                        dict[ap['id']]['antennaHeight'] = radio['antennaHeight']
                        if radio['antennaMounting'] == "CEILING":
                            dict[ap['id']]['antennaOrientation'] = "Horizontal"
                        elif radio['antennaMounting'] == "WALL":
                            dict[ap['id']]['antennaOrientation'] = "Vertical"
                        else:
                            dict[ap['id']]['antennaOrientation'] = "Unknown"
        for antenna in jsons['antenna']:
            if dict[ap['id']]['antennaId'] == antenna['id']:
                if antenna['apCoupling'] == "EXTERNAL_ANTENNA":
                    dict[ap['id']]['apCoupling'] = antenna['apCoupling']
                    dict[ap['id']]['antennaName'] = antenna['name']
                elif antenna['apCoupling'] == "INTERNAL_ANTENNA":
                    dict[ap['id']]['apCoupling'] = antenna['apCoupling']
                    dict[ap['id']]['antennaName'] = " "
        for note in jsons['notes']:
            if note['status'] == "DELETED":
                continue
            if note['text'] == ap['name']:
                for cable in jsons['cablenotes']:
                    for cable_note_id in cable['noteIds']:
                        if cable_note_id == note['id']:
                            length = round(calculate_cable_length(dict[ap['id']]['mpu'], cable['points']))
                            dict[ap['id']]['distancetoIDF'] = str(length) + "m"
                            error = False
        error = False
    return dict, error


def calculate_cable_length(meterPerUnit: float, points: list) -> float:
    length = 0
    x = 0
    y = 0
    i = 0

    for coords in points:
        if i == 0:
            x = coords['x']
            y = coords['y']
            i = i + 1
        else:
            if x != coords['x'] and y != coords['y']:
                if x > coords['x'] and y > coords['y']:
                    length = length + math.sqrt(((x - coords['x']) ** 2) + ((y - coords['y']) ** 2))
                elif x < coords['y'] and y > coords['y']:
                    length = length + math.sqrt(((coords['x'] - x) ** 2) + ((y - coords['y']) ** 2))
                elif x > coords['y'] and y < coords['y']:
                    length = length + math.sqrt(((x - coords['x']) ** 2) + ((coords['y'] - y) ** 2))
                elif x < coords['y'] and y < coords['y']:
                    length = length + math.sqrt(((coords['x'] - x) ** 2) + ((coords['y'] - y) ** 2))
            elif x != coords['x']:
                if x > coords['x']:
                    length = length + (x - coords['x'])
                else:
                    length = length + (coords['x'] - x)
            else:
                if y > coords['y']:
                    length = length + (y - coords['y'])
                else:
                    length = length + (coords['y'] - y)
            x = coords['x']
            y = coords['y']

    return length * meterPerUnit


if __name__ == "__main__":
    main()
