# Ben Hickson
# bhickson@email.arizona.edu

# University of Arizona, Library

# Metadata Editing Tool

## This script creates a GUI interface for the editing of geospatial metadata.
##    Following the Open GeoPortals Metadata Best Practices Guide, the tool focuses
##    on critical metadata fields only.  In addition to editing/compiling the
##    datasets metadata, the tool will force for file re-naming corresponding to the
##    Location_Theme_Year format recommended by GeoMAPP. Current support is only for
##    shapefiles, though this can easily be changed in the script.  The initial
##    window (first_frame_master) allows you to select the input and output
##    directories for reading and writing, as well as any default info that will
##    likely be uniform across all datasets (Host Insitution, Contact Info, etc.).
##    A persistent unique identifiers (PUI) prefix field is also here.  The
##    University of Arizona will be using registered DOI for PUI, so it is
##    included in this section.  As each dataset is edited, a copy of the xml
##    file is created in the folder tmpXMLFiles, which itself will be created in
##    the input data directory.  This is done so that no changes will be made to the
##    original file.  In order to proceed to the next dataset, all fields must be filled
##    in and updated with the "Update Fields" button (or the dataset can be skipped
##    with SKIP).  For the theme keywords section, the program will look for a themekey
##    thesaurus (themekt element) with the value,"ISO 19115 Topic Category".  If it is
##    not found, it will created a new parent theme element (theme) with a child
##    themekt element "ISO 19115 Topic Category". Any theme keywords (themekey)
##    elements created from here will be created under this theme parent.  The OGP
##    metadata best practices recommend that Place Keywords follow the GNS thesaurus.
##    This has not been tied into the program, though the practice should be followed
##    through external reference.  Once all datasets have been iterated through, the
##    final frame will give a summary.


import os, sys, arcpy, collections, math, shutil, webbrowser, time, getpass, re
import xml.etree.ElementTree as ET
from tkFileDialog import askdirectory
from Tkinter import *

global updateXML_Ran
updateXML_Ran = False
global count
count = 0
rowNum = 0

global datasets
datasets = []
global mod_Datasets
mod_Datasets = {}
global skipped_Datasets
skipped_Datasets = []
puidEntry = ""
outdir_OK = False


try:
    GNIS_File = open(r"C:\Users\hicksonb\Downloads\UAiR\AZ_Features_20150601.csv", "r")
    autocompleteList = GNIS_File.read().split(",")
except:
    autocompleteList = []
    noteRoot = Tk()
    noteRoot.wm_title("Alert")
    notification  = Label(noteRoot, text = """
    A csv file containing the GNIS names was not found.
    Please either downloaded the GNIS names file from the link
    below and process the subjects into simple comma
    separated values, or use the GNIS website to search
    for the appropriate subject name

    """)
    notification.grid(row = 0, column = 0)
    #notification.config(justify = LEFT, anchor = W)

    gnis = Button(noteRoot, text = "GNIS Names Search", command = lambda: webbrowser.open("http://geonames.usgs.gov/apex/f?p=136:1:4191006979861"))
    gnis.grid(row = 1, column = 0, padx = 5, pady = 10, sticky = N)


    gnisDownload = Button(noteRoot, text = "GNIS Names Download", command = lambda: webbrowser.open("http://geonames.usgs.gov/domestic/download_data.htm"))
    gnisDownload.grid(row = 2, column = 0, padx = 5, pady = 10, sticky = N)

    ok = Button(noteRoot, text = "Continue", command = noteRoot.destroy)
    ok.grid(row = 3, column = 0, padx = 20, pady = 20, sticky = (S,E))

    def close():
        noteRoot.destroy()
        sys.exit("Exited Program")

    exit = Button(noteRoot, text = "Exit", command = close)
    exit.grid(row = 3, column = 0, padx = 20, pady = 20, sticky = (S,W))


    noteRoot.mainloop()


idir = ''  #DEFAULT INPUT DIRECTORY
cwd = os.getcwd()
cwd = cwd.replace('\\', '/') + '/'


"""
Credit for this class goes to user uroshekic on github for providing structural code
used to build the AutoComplete Entry.
https://gist.github.com/uroshekic/11078820
"""
class AutocompleteEntry(Entry):
    def __init__(self, autocompleteList, *args, **kwargs):

        # Listbox length
        if 'listboxLength' in kwargs:
            self.listboxLength = kwargs['listboxLength']
            del kwargs['listboxLength']
        else:
            self.listboxLength = 15

        # Custom matches function
        if 'matchesFunction' in kwargs:
            self.matchesFunction = kwargs['matchesFunction']
            del kwargs['matchesFunction']
        else:
            def matches(fieldValue, acListEntry):
                pattern = re.compile(re.escape(fieldValue) + '.*', re.IGNORECASE)
                return re.match(pattern, acListEntry)

            self.matchesFunction = matches
        if 'row' in kwargs:
            self.lbRow = int(kwargs['row'])+1
            del kwargs['row']
        else:
            self.lbRow = 40

        if 'initialValue' in kwargs:
            self.initialValue = kwargs['initialValue']
            del kwargs['initialValue']
        else:
            self.initialValue = False

        Entry.__init__(self, *args, **kwargs)
        self.focus()

        self.autocompleteList = autocompleteList

        self.var = self["textvariable"]
        if self.var == '':
            self.var = self["textvariable"] = StringVar()


        self.var.trace('w', self.changed)
        self.bind("<Right>", self.selection)
        self.bind("<Return>", self.selection)
        self.bind("<Up>", self.moveUp)
        self.bind("<Down>", self.moveDown)
        self.bind("<Escape>", self.exit)

        self.listboxUp = False

    def exit(self, event):
        self.listbox.grid_forget()


    def changed(self, name, index, mode):
        if self.initialValue is True:
            try:
                self.listbox.destroy()
            except:
                pass
            self.initialValue = False

        elif self.var.get() == '':
            if self.listboxUp:
                self.listbox.destroy()
                self.listboxUp = False
        else:
            words = self.comparison()
            if words:
                if not self.listboxUp:
                    self.listbox = Listbox(second_frame, width=self["width"], height=self.listboxLength, bg = "#E0E0E0")
                    self.listbox.bind("<Button-1>", self.selection)
                    self.listbox.bind("<Right>", self.selection)
                    self.listbox.grid(column = 1, row = self.lbRow, rowspan = 10,sticky = (N,W))
                    self.listboxUp = True

                self.listbox.delete(0, END)
                for w in words:
                    self.listbox.insert(END,w)
            else:
                if self.listboxUp:
                    self.listbox.destroy()
                    self.listboxUp = False

    def selection(self, event):
        if self.listboxUp:
            self.var.set(self.listbox.get(ACTIVE))
            self.listbox.destroy()
            self.listboxUp = False
            self.icursor(END)

    def moveUp(self, event):
        if self.listboxUp:
            if self.listbox.curselection() == ():
                index = '0'
            else:
                index = self.listbox.curselection()[0]

            if index != '0':
                self.listbox.selection_clear(first=index)
                index = str(int(index) - 1)

                self.listbox.see(index) # Scroll!
                self.listbox.selection_set(first=index)
                self.listbox.activate(index)

    def moveDown(self, event):
        if self.listboxUp:
            if self.listbox.curselection() == ():
                index = '0'
            else:
                index = self.listbox.curselection()[0]

            if index != END:
                self.listbox.selection_clear(first=index)
                index = str(int(index) + 1)

                self.listbox.see(index) # Scroll!
                self.listbox.selection_set(first=index)
                self.listbox.activate(index)

    def comparison(self):
        return [ w for w in self.autocompleteList if self.matchesFunction(self.var.get(), w) ]
    """
    ----------------------------------------------------------------------------------------------------------------
    """


def xmlFields(type):
    # CREATE DICTIONARIES THAT WILL CONTAIN THE KEY/VALUE PAIRS BY ORDER ADDED
    global xmlDict
    xmlDict = collections.OrderedDict()
    global distInfoDict
    distInfoDict = collections.OrderedDict()
    global metaInfoDict
    metaInfoDict = collections.OrderedDict()
    global xmlProcessStep
    xmlProcessStep = collections.OrderedDict()

    global metadatalangType
    metadatalangType = ["eng","spa"]  # CURRENTLY NOT IN USE

    global isoTopicCategories
    isoTopicCategories = ["farming", "biota", "boundaries", "climatologyMeterologyAtmosphere", "economy",
        "elevation", "environment", "geoscientificInformation", "health", "imageryBaseMapsEarthCover",
        "intelligenceMilitary", "inlandWater", "location", "oceans", "planningCadastre", "society", "structure",
        "transportation", "utilitiesCommunication"]

    global accessConstraints
    accessConstraints = ["Restriced Access Online - available only to persons affiliated with the University of Arizona",
    "Unrestricted Access - publicly available dataset"]
    global accessConstOptions
    accessConstOptions = ["Restriced Access Online","Unrestricted Access"]

    """ IF ADDING SUPPORT FOR ISO 19139, ESRI, DUBLIN, OR OTHER, NEED TO MAP THE PATH OF THE NECESSARY XML TAGS HERE. """
    simpleDataType = []
    sourceDataType = []

    if type is "FGDC":

        global simpleDataType
        global sourceDataType

        xmlDict["Title"] =                              ["idinfo","citation","citeinfo","title"]
        xmlDict["Data Type"] =                          ["dataqual","lineage","srcinfo","typesrc"]
        xmlDict["Northern Bounding Edge"] =             ["idinfo","spdom","bounding","northbc"]
        xmlDict["Southern Bounding Edge"] =             ["idinfo","spdom","bounding","southbc"]
        xmlDict["Eastern Bounding Edge"] =              ["idinfo","spdom","bounding","eastbc"]
        xmlDict["Western Bounding Edge"] =              ["idinfo","spdom","bounding","westbc"]
        xmlDict["Originator"] =                         ["idinfo","citation","citeinfo","origin"]
        xmlDict["Abstract"] =                           ["idinfo","descript","abstract"]
        xmlDict["Purpose"] =                            ["idinfo","descript","purpose"]
        xmlDict["Publisher"] =                          ["idinfo","citation","citeinfo","pubinfo","publish"]
        xmlDict["Publication Date (YYYY-MM-DD)"] =      ["idinfo","citation","citeinfo","pubdate"]
        xmlDict["Date of Content"] =                    ["idinfo","timeperd","timeinfo","sngdate","caldate"] #This element has the option of being a single date/time (sngdate/time), multiple dates/times, or a range of dates/times.  Should add functionality for theses?        #xmlDict["Host Institution"] =                   ["distinfo","distrib"]
        xmlDict["Online Location"] =                    ["idinfo","citation","citeinfo","onlink"]
        xmlDict["Access Constraints"] =                 ["idinfo","accconst"]
        xmlDict["Use Constraints"] =                    ["idinfo","useconst"]
        xmlDict["Theme Keywords (ISO 19115 Topics)"] =  ["idinfo","keywords","theme","themekey"]
        xmlDict["Place Keywords (GNIS)"] =              ["idinfo","keywords","place","placekey"]
        #xmlDict["Metadata Language"] =                 ["metainfo","metalang"]  # Not currently a field for metadata language for FGDC
        xmlDict["Horizontal Datum"] =                   ["spref","horizsys","geodetic","horizdn"]
        xmlDict["Simple Data Type"] =                   ["spdoinfo","ptvctinf","sdtsterm","sdtstype"]

        xmlDict["Persistent Identifier"] =              ["distinfo","resdesc"] # As per FGDC "the identifier by which the distributor knows the data set."

        distInfoDict["Person"] =                        ["distinfo","distrib","cntinfo","cntorgp","cntper"]
        distInfoDict["Organization"] =                  ["distinfo","distrib","cntinfo","cntorgp","cntorg"]
        distInfoDict["Address Type"] =                  ["distinfo","distrib","cntinfo","cntaddr","addrtype"]
        distInfoDict["Address"] =                       ["distinfo","distrib","cntinfo","cntaddr","address"]
        distInfoDict["City"] =                          ["distinfo","distrib","cntinfo","cntaddr","city"]
        distInfoDict["State"] =                         ["distinfo","distrib","cntinfo","cntaddr","state"]
        distInfoDict["Postal Code"] =                   ["distinfo","distrib","cntinfo","cntaddr","postal"]
        distInfoDict["Country"] =                       ["distinfo","distrib","cntinfo","cntaddr","country"]
        distInfoDict["Email"] =                         ["distinfo","distrib","cntinfo","cntemail"]

        metaInfoDict["Metadata Date"] =                 ["metainfo","metd"]
        metaInfoDict["Metadata Author"] =               ["metainfo","metc","cntinfo","cntorgp","cntper"]
        metaInfoDict["Metadata Organization"] =         ["metainfo","metc","cntinfo","cntorgp","cntorg"]

        xmlProcessStep["Process Description"] =         ["dataqual","lineage","procstep","procdesc"]
        xmlProcessStep["Process Date"] =                ["dataqual","lineage","procstep","procdate"]
        xmlProcessStep["Process Time"] =                ["dataqual","lineage","procstep","proctime"]


        # SELECTABLE OPTIONS FOF DROP DOWNS
        sourceDataTypesOptions = ["computer program", "paper" , "stable-base material" , "microfiche" , "microfilm" , "audiocassette" ,
        "chart" , "filmstrip" , "transparency" , "videocassette" , "videodisc" , "videotape" ,
        "physical model" , "disc" , "cartridge tape" , "magnetic tape" ,
        "online" , "CD-ROM" , "electronic bulletin board" , "electronic mail system"]
        simpleDataTypesOptions = ["Point", "String", "Arc", "G-ring", "G-Polygon", "Grid", "Raster"]

        for option in sourceDataTypesOptions:
            sourceDataType.append(option)
        for option in simpleDataTypesOptions:
            simpleDataType.append(option)

# FUNCTION THAT WILL BE BOUND TO TEXT WIDGETS TO REMOVE TAB INDENTATION FROM THEM AND INSTEAD FOCUS ON NEXT TEXT WIDGET.
def focus_next_window(event):
    event.widget.tk_focusNext().focus()
    return("break")

# FUNCTION THAT WILL CREATE LABELS AND TEXT FIELDS FOR ALL XML ELEMENTS
def xmlElementsLabels(metadataType,file):
    global modifiedFiles_Log
    modifiedFiles_Log.write("Metadata found of type " + metadataType +"\n")
    # THIS DICTIONARY IS USED TO ASSOCIATES EACH CREATED WIDGET TO THE SPECIFIC ELEMENT IN THE XML TREE.
    #   CRITICAL TO USE WIDGET ID # AS THE KEY, AS NO OTHER UNIQUE VARIABLE CAN BE USED TO LOCATE THE INDIVIDAUL WIDGET.
    #   THE DICTIONARY IS USED TO ASSOCIATE THE WIDGET ID NUMBER TO THE ELEMENT PATH AND INDEX NUMBER SO THAT THE
    #   WIDGET VALUE CAN BE WRITTEN TO THE APPROPRIATE ELEMENT.
    global widgetDict
    widgetDict = {}

    xmlFields(metadataType)  # Call xmlFields function with the idenified metadataType variable

    global typesrcVars
    typesrcVars = []  # Create empty list to insert StringVar's into for typesrc Menu options.  Need to do this so that each menu has it's own variable.  Otherwise, all menus of this type will map to the same variable.

    global sdtstypeVars
    sdtstypeVars = []  # Same reasoning as typesrcVars

    global isoTopicCategoryVars
    isoTopicCategoryVars = [] # Same reasoning as typesrcVars

    global metadatalangVar
    metadatalangVar = StringVar(second_frame)  # the metadatalang menu will only only map to one element, no need for a list of string variables
    metadatalangVar.set(metadatalangType[0])

    global accessConst_Var
    accessConst_Var = StringVar(second_frame)
    accessConst_Var.set(accessConstOptions[1])

    global rowNum
    rowNum = 3 #this is set at row 3 so that the list begins below the Dataset Name Label

    # PARSE XML FILE AND IDENTIFY FIRST ROOT...

    print "FILE: ", file
    global theRoot
    theRoot = ET.parse(file)

    global treeRoot
    treeRoot = theRoot.find(".")
    if treeRoot.tag != "metadata":
        issueText =\
        "Metadata tree root element was identified to not be compatible with with the editor.\n Recommend skipping dataset."
        createNotificationWindow(issueText)

    # BEGIN ITERATING THROUGH XML FILE LOOKING THE PATH OF EACH NECESSARY METADATA TAG IDENTIFIED IN xmlDict
    for key in xmlDict:
        """print key"""
        # CREATE LABEL FOR THE METADATA ELEMENT
        elementTag_Label = Label(second_frame, text = key)
        elementTag_Label.grid(row = rowNum, column = 0, columnspan= 1,sticky=(E,N))
        elementPath = "."

        for subElement in range(len(xmlDict[key])):
            oldPath = elementPath
            elementPath+="/"+xmlDict[key][subElement]
            """print elementPath

            print "SUB-ELEMENT",xmlDict[key][subElement]
            print "ELEMENT PATH:",elementPath"""

            #ATTEMPT TO FIND THE CURRENT XML TAG AT THE CURRENT ITERATION IN DICTIONARY KEY VALUE
            elementTest =treeRoot.find(elementPath)

            #IF THE XML TAG ISN'T FOUND AT THE PATH SPECIFIED, CREATE THE TAG AT THAT PATH
            if elementTest is None:
                """print "PATH TO WRITE TO:",oldPath
                print "NEW ELEMENT TO BE CREATED:",xmlDict[key][subElement]"""
                newPath = theRoot.find(oldPath)
                ET.SubElement(newPath,xmlDict[key][subElement])
                """print xmlDict[key][subElement],"not found.  Adding." """

        if key == "Theme Keywords (ISO 19115 Topics)":
            themes = treeRoot.findall("./idinfo/keywords/theme")
            for theme in themes:

                try:
                    if theme.find("themekt").text == "ISO 19115 Topic Category":    # # IF AN ELEMENT themekt IS FOUND, AND WHOSE VALUE IS "ISO 19115 Topic Category," SET iso_Theme TO THE CURRENT theme ELEMENT.
                        iso_Theme = theme
                        break
                    else:   # IF AN ELEMENT themekt IS FOUND, BUT WHOSE VALUE IS NOT "ISO 19115 Topic Category," SET iso_Theme TO None
                        iso_Theme = None
                except:     # IF NO themekt ELEMENT IS FOUND ANYWHERE, SET iso_Theme TO None
                    iso_Theme = None
            if iso_Theme is None:
                iso_Theme = ET.SubElement(treeRoot.find("./idinfo/keywords"),"theme")
                iso_ThemeKT = ET.SubElement(iso_Theme,"themekt")
                iso_Element = ET.SubElement(iso_Theme,"themekey")
                iso_ThemeKT.text = "ISO 19115 Topic Category"

            elements = iso_Theme.findall("themekey")

        elif key == "Place Keywords (GNIS)":
            themes = treeRoot.findall("./idinfo/keywords/place")
            for theme in themes:
                try:
                    if theme.find("placekt").text == "GNIS" or theme.find("placekt").text == "Geographic Names Information System":    # # IF AN ELEMENT themekt IS FOUND, AND WHOSE VALUE IS "ISO 19115 Topic Category," SET iso_Theme TO THE CURRENT theme ELEMENT.
                        gnis_Theme = theme
                        break
                    else:   # IF AN ELEMENT themekt IS FOUND, BUT WHOSE VALUE IS NOT "ISO 19115 Topic Category," SET iso_Theme TO None
                        gnis_Theme = None
                except:     # IF NO themekt ELEMENT IS FOUND ANYWHERE, SET iso_Theme TO None
                    gnis_Theme = None
            if gnis_Theme is None:
                gnis_Theme = ET.SubElement(treeRoot.find("./idinfo/keywords"),"place")
                gnis_PlaceKT = ET.SubElement(gnis_Theme,"placekt")
                gnis_Element = ET.SubElement(gnis_Theme,"placekey")
                gnis_PlaceKT.text = "GNIS"

            elements = gnis_Theme.findall("placekey")

        else:
            elements = treeRoot.findall(elementPath) # FIND ALL ELEMENTS AT elementPath FOR EVERYTHING NOT "Theme Keywords (ISO 19115 Topics)" or "Place Keywords (GNIS)".

        global parentPath
        parentPath = "."
        for tagNum in range(len(xmlDict[key])-1):
            parentPath += "/"+ xmlDict[key][tagNum]  # BUILD PARENT PATH FROM VALUES LIST
        parents = treeRoot.findall(parentPath)

        # ONCE THE NECESSARY TAG HAS BEEN IDENTIFIED OR CREATED, CREATE LABEL AND TEXT ENTRY BOX. IF THERE ARE
        #           MULTIPLE TAGS FOR THE KEY, CREATE MULTIPLE TEXT ENTRIES
        entryRow = rowNum

        for element in elements:
            numLines = 1                # DEFAULT HEIGHT OF ALL TEXT WIDGETS
            content = element.text      # TEXT CONTENT OF THE ELEMENT
            global indexNum
            for par in parents:      # MATCHES ELEMENT TO THE APPROPRIATE PARENT (IF MULTIPLE) AND GETS CHILD INDEX NUMBER UNDER THAT PARENT
                # NOTE THIS WAS CAUSING ISSUES WITH MULTIPLE PARENTS WITH THE SAME
                try:
                    indexNum = list(par).index(element)
                    parent = par     # ASSIGN PARENT VARIABLE TO THIS ITERATION OF ELEMENTS
                except:
                    pass

            if key =="Simple Data Type":
                sdtstypeVars.append(StringVar(second_frame))  # Creates String variable (StringVar) and adds it to the list sdtstypeVars

                sdtstypeMenu = apply(OptionMenu, (second_frame, sdtstypeVars[-1]) + tuple(simpleDataType)) # [-1] Makes sure that menu uses the last variable added in sdtstypeVars list.
                sdtstypeMenu.grid(row= entryRow, column= 1,columnspan= 2, sticky= W)
                sdtstypeMenu.config(bg="grey")

                previousValue = Label(second_frame, text = "Current Value : " + str(content))
                previousValue.grid(row= entryRow, column= 3, columnspan= 2, sticky= W)

                widgetDict[sdtstypeMenu.winfo_id()] = [key]
                widgetDict[sdtstypeMenu.winfo_id()].append(element)
                widgetDict[sdtstypeMenu.winfo_id()].append(parent)
                widgetDict[sdtstypeMenu.winfo_id()].append(indexNum)

            elif key == "Data Type":
                typesrcVars.append(StringVar(second_frame)) # Creates String variable (StringVar) and adds it to the list typesrcVars

                typesrcMenu = apply(OptionMenu, (second_frame, typesrcVars[-1]) + tuple(sourceDataType))  # Make sure that menu uses the last variable added in typesrcVars list.  Could have also used [0] as 0 index will change with each addition.
                typesrcMenu.grid(row = entryRow, column =1,columnspan = 2, sticky =W)
                typesrcMenu.config(bg="grey")

                previousValue = Label(second_frame, text = "Current Value : " + str(content))  # Show previous (Current) value found at the element's path.
                previousValue.grid(row= entryRow, column= 3, columnspan= 2, sticky= W)

                # THIS SECTION ASSOCIATES EACH CREATED WIDGET TO THE SPECIFIC ELEMENT IN THE XML TREE.  CRITICAL TO USE WIDGET ID #, AS NO OTHER UNIQUE VARIABLE CAN BE USED TO LOCATE THE WIDGET
                widgetDict[typesrcMenu.winfo_id()] = [key]      # Add the widget id of typesrcMenu as a key to widget Dict with the key value of xmlDict as the value, which is in a list
                widgetDict[typesrcMenu.winfo_id()].append(element)  #  Add the elementPath to the values for this widget id key in widget Dict
                widgetDict[typesrcMenu.winfo_id()].append(parent)
                widgetDict[typesrcMenu.winfo_id()].append(indexNum)   #  Add the index number of the element under the parent to the values for the widget id key in widgetDict

            elif key == "Metadata Language":
                metalangMenu = apply(OptionMenu, (second_frame, metadatalangVar) + tuple(metadatalangType))
                metalangMenu.grid(row = entryRow, column =1,columnspan = 2, sticky =W)
                metalangMenu.config(bg="grey")

                previousValue = Label(second_frame, text = "Current Value : " + str(content))
                previousValue.grid(row= entryRow, column= 3, columnspan= 2, sticky= W)

                widgetDict[metalangMenu.winfo_id()] = [key]
                widgetDict[metalangMenu.winfo_id()].append(element)
                widgetDict[metalangMenu.winfo_id()].append(parent)
                widgetDict[metalangMenu.winfo_id()].append(indexNum)

            elif key == "Access Constraints":
                accessConst_Menu = apply(OptionMenu, (second_frame, accessConst_Var) + tuple(accessConstOptions))
                accessConst_Menu.grid(row = entryRow, column =1,columnspan = 2, sticky =W)
                accessConst_Menu.config(bg="grey")


                widgetDict[accessConst_Menu.winfo_id()] = [key]
                widgetDict[accessConst_Menu.winfo_id()].append(element)
                widgetDict[accessConst_Menu.winfo_id()].append(parent)
                widgetDict[accessConst_Menu.winfo_id()].append(indexNum)

            elif key == "Theme Keywords (ISO 19115 Topics)":

                themeParent = parent
                themeElementTag = element.tag
                themeKeywordNum = indexNum
                themeElement = element

                def addThemeElement():
                    # THIS FUNCTION WILL USE THE ADD BUTTON TO WRITE A NEW ELEMENT UNDER THE PARENT TAG IDENTIFIED FOR THEME KEYWORDS
                    global count

                    ET.SubElement(themeParent,themeElementTag)          # THE NEW CHILD ELEMENT IS ADDED
                    write_widget_values_to_XML(False)
                    theRoot.write(file)                                 # WRITE THE CHANGES BACK TO THE FILE
                    widgetlist = second_frame.winfo_children()          # THIS SECTION REMOVES WIDGETS FROM SECOND_FRAME FRAME.
                    for widget in widgetlist :
                        widget.destroy()
                    # BECAUSE FUNCTION create_widgets_in_second_frame() WILL ADD 1 TO COUNT BEFORE ITERATING THROUGH
                    #     DATASETS LIST INDEX, WE NEED TO SUBSTRACT FROM COUNT TO ITERATE OVER THE SAME DATASET AGAIN.
                    count-=1
                    create_widgets_in_second_frame()                    # RECREATE SECOND FRAME WITH SAME DATASET

                def removeThemeElement(index):
                    # THIS FUNCTION USES THE REMOVE BUTTON TO REMOVE THE LAST MATCHING ELEMENT FROM PARENT ELEMENT FOR THEME KEYWORDS
                    global count
                    tag=themeParent[index]                              # SET THE ELEMENT TO THE INDEX VALUE UNDER PARENT
                    for k in list(widgetDict):
                        try:
                            if widgetDict[k][1] == themeElement and widgetDict[k][3] == index:
                                del widgetDict[k]
                        except:
                            pass
                    themeParent.remove(tag)                             # REMOVE THE CHILD ELEMENT FROM PARENT ELEMENT
                    write_widget_values_to_XML(False)                   # WRITE THE CURRENT WIDGET VALUES TO FILE IN MEMORY SO THAT WHEN FRAME IS RECREATED BELOW, CHANGES ARE NOT LOST.
                    theRoot.write(file)                                 # WRITE THE CHANGES TO XML FILE IN MEMORY BACK TO THE SOURCE FILE IN TEMP FOLDER
                    widgetlist = second_frame.winfo_children()          # REMOVE ALL WIDGETS FROM SECOND_FRAME FRAME.
                    for widget in widgetlist :
                        widget.destroy()
                    # BECAUSE FUNCTION create_widgets_in_second_frame() WILL ADD 1 TO COUNT BEFORE ITERATING THROUGH
                    #     DATASETS LIST INDEX, WE NEED TO SUBSTRACT FROM COUNT TO ITERATE OVER THE SAME DATASET AGAIN.
                    count -= 1
                    create_widgets_in_second_frame()                    # RECREATE WIDGETS IN SECOND_FRAME FRAME

                isoTopicCategoryVars.append(StringVar(second_frame))  # Creates String variable (StringVar) and adds it to the list isoTopicCategoryVars

                isoThemeMenu = apply(OptionMenu, (second_frame, isoTopicCategoryVars[-1]) + tuple(isoTopicCategories))
                isoThemeMenu.grid(row = entryRow, column = 1, columnspan =2, sticky = W)
                isoThemeMenu.config(bg="grey")
                if content is not None:
                    isoTopicCategoryVars[-1].set(content)


                if element == elements[-1]:    # THIS WILL ONLY CREATE THE ADD BUTTON NEXT TO THE THE LAST MATCHING CHILD ELEMENT UNDER PARENT ELEMENT
                    addButton = Button(second_frame,text = "Add", command = addThemeElement)
                    addButton.grid(row= entryRow, column = 5, sticky= W)
                if element == elements[-1] and element != elements[0]:  # SAME AS ADD BUTTON, BUT WILL NOT BE AVAILABLE IF THERE IS ONLY ONE CHILD ELEMENT
                    removeButton = Button(second_frame,text = "Remove", command = lambda: removeThemeElement(themeKeywordNum))
                    removeButton.grid(row= entryRow, column = 6, sticky= W)

                widgetDict[isoThemeMenu.winfo_id()] = [key]
                widgetDict[isoThemeMenu.winfo_id()].append(element)
                widgetDict[isoThemeMenu.winfo_id()].append(parent)
                widgetDict[isoThemeMenu.winfo_id()].append(indexNum)

            elif key == "Persistent Identifier":
                # THIS WIDGET VALUE WILL NOT BE EDITABLE, BUT WILL BE POPULATED FROM THE PERSISTENT IDENTIFIER PREFIX FROM THE FIRST FRAME AND THE FILE NAME
                """ NOTE DEPENDING ON ELEMENT MAPPING, THIS COULD CAUSE PROBLEMS WITH FUTURE SUPPORT FOR ISO """

                global puid
                puid = Label(second_frame, text = "{will auto update with file name update}", background = '#FFFAFA',relief='groove')#,font='bold')
                puid.grid(row = entryRow, column = 1, columnspan = 4, stick = W)

                widgetDict[puid.winfo_id()] = [key]
                widgetDict[puid.winfo_id()].append(element)
                widgetDict[puid.winfo_id()].append(parent)
                widgetDict[puid.winfo_id()].append(indexNum)


            elif key == "Place Keywords (GNIS)":

                placeParent = parent
                placeElementTag = element.tag
                placeKeywordNum = indexNum
                placeElement = element

                def addPlaceElement():
                    # FUNCTION IS IDENTICAL TO addThemeElement FUNCTION.  SEE ABOVE.
                    global count
                    ET.SubElement(placeParent,placeElementTag)
                    write_widget_values_to_XML(False)
                    theRoot.write(file)
                    widgetlist = second_frame.winfo_children()
                    for widget in widgetlist :
                        widget.destroy()

                    count-=1
                    create_widgets_in_second_frame()

                def removePlaceElement(index):
                    # THIS FUNCTION USES THE REMOVE BUTTON TO REMOVE THE LAST MATCHING ELEMENT FROM PARENT ELEMENT FOR THEME KEYWORDS
                    global count
                    tag=placeParent[index]                              # SET THE ELEMENT TO THE INDEX VALUE UNDER PARENT
                    for k in list(widgetDict):
                        try:
                            if widgetDict[k][1] == placeElement and widgetDict[k][3] == index:
                                del widgetDict[k]
                        except:
                            pass
                    placeParent.remove(tag)                             # REMOVE THE CHILD ELEMENT FROM PARENT ELEMENT
                    write_widget_values_to_XML(False)                   # WRITE THE CURRENT WIDGET VALUES TO FILE IN MEMORY SO THAT WHEN FRAME IS RECREATED BELOW, CHANGES ARE NOT LOST.
                    theRoot.write(file)                                 # WRITE THE CHANGES TO XML FILE IN MEMORY BACK TO THE SOURCE FILE IN TEMP FOLDER
                    widgetlist = second_frame.winfo_children()          # REMOVE ALL WIDGETS FROM SECOND_FRAME FRAME.
                    for widget in widgetlist :
                        widget.destroy()
                    # BECAUSE FUNCTION create_widgets_in_second_frame() WILL ADD 1 TO COUNT BEFORE ITERATING THROUGH
                    #     DATASETS LIST INDEX, WE NEED TO SUBSTRACT FROM COUNT TO ITERATE OVER THE SAME DATASET AGAIN.
                    count -= 1
                    create_widgets_in_second_frame()                    # RECREATE WIDGETS IN SECOND_FRAME FRAME


                PlaceKey_Entry = AutocompleteEntry(autocompleteList, second_frame, listboxLength=15, width=50, row = entryRow, initialValue = True)
                PlaceKey_Entry.grid(row = entryRow, column = 1, columnspan =2, sticky = W)
                if content is not None:
                    PlaceKey_Entry.insert(0, content)

                if element == elements[-1]:
                    addButton = Button(second_frame,text = "Add", command = addPlaceElement)
                    addButton.grid(row= entryRow, column = 5, sticky= W)
                if element == elements[-1] and element != elements[0]:
                    removeButton = Button(second_frame,text = "Remove", command = lambda: removePlaceElement(placeKeywordNum))
                    removeButton.grid(row= entryRow, column = 6, sticky= W)

                widgetDict[PlaceKey_Entry.winfo_id()] = [key]
                widgetDict[PlaceKey_Entry.winfo_id()].append(element)
                widgetDict[PlaceKey_Entry.winfo_id()].append(parent)
                widgetDict[PlaceKey_Entry.winfo_id()].append(indexNum)

            else:
                def contentSearch(defaultWidget, widgetText):
                    defaultText = defaultWidget.get(1.0, "end")[0:-1]
                    if widgetText == None:
                        newContent = defaultText       # IF THE ELEMENT HAS NO TEXT (E.G. None), SET CONTENT TO DEFAULT WIDGET TEXT
                    elif widgetText.find(defaultText) == -1:
                        newContent = widgetText + "\n\n" + defaultText # IF THE DEFAULT TEXT IS NOT FOUND IN THE EXISTING ELEMENT CONTENT, APPEND IT TO THE END
                    else:
                        newContent = widgetText # IF THE DEFAULT TEXT IS FOUND IN THE EXISTING ELEMENT CONTENT, DO NOTHING

                    return newContent

                """ UA wanted to preserve the original purpose and use contraints, if either was definied, and append default portal info after. This appends to the end if text already exists."""
                if key == "Use Constraints":
                    content = contentSearch(useConst_Text, content)
                elif key == "Purpose":
                    content = contentSearch(purpose_Text, content)

                if key == "Online Location":        # INSERT DEFAULT VALUES SPECIFIED IN FIRST FRAME INTO THE Online Location WIDGET
                    content = defaultInputValues[0]


                # IF THERE IS TEXT IN THE XML TAG, CREATE A TEXT WIDGET WITH OF APPROPRIATE HEIGHT (LINES), AND INSERT THE CONTENT
                if content is not None:
                    numLines = int(math.ceil(float(len(content))/60))  #the number of lines the tag text content will take up with field length of 60
                    for char in content:
                        if char == "\n":
                            numLines += 1
                # IF THERE IS NOT TEXT IN THE XML TAG, CREATE EMPTY SINGLE LINE TEXT FIELD
                else:
                    content = ""


                xmlTextContent = Text(second_frame, width = 60, height = numLines, wrap="word")
                xmlTextContent.grid(row=entryRow,column=1,columnspan=4,stick=W)
                xmlTextContent.insert(1.0,content)


                widgetDict[xmlTextContent.winfo_id()] = [key]
                widgetDict[xmlTextContent.winfo_id()].append(element)
                widgetDict[xmlTextContent.winfo_id()].append(parent)
                widgetDict[xmlTextContent.winfo_id()].append(indexNum)
                widgetDict[xmlTextContent.winfo_id()].append(xmlTextContent)

            # ENSURE THAT IF THERE ARE MULTIPLE XML TAGS FOR THIS KEY THAT THEY ARE CREATED BELOW EACH OTHER
            entryRow+=numLines

        # ENSURE THAT THE NEXT KEY LABEL AND TEXT FIELD ARE CREATED BELOW THE PREVIOUS SET
        oldRowNum = rowNum
        rowNum+=entryRow-oldRowNum

    second_frame.bind_class("Text","<Tab>",focus_next_window) # ALLOW USER TO CYCLE THROUGH TEXT WIDGETS WITH TAB KEY

    try:
        distContact = theRoot.find("distinfo","distrib","cntinfo")  # CLEAR OUT CURRENT DISTRIBUTOR CONTACT INFO
        distContact.clear()
    except:
        pass

    for k,v in distInfoDict.items():
        global distInfoWidgets
        elementPath = "."
        for subElement in v:
            oldPath = elementPath
            elementPath+="/"+ subElement

            #ATTEMPT TO FIND THE CURRENT XML TAG AT THE CURRENT ITERATION IN DICTIONARY KEY VALUE
            elementTest =treeRoot.find(elementPath)

            #IF THE XML TAG ISN'T FOUND AT THE PATH SPECIFIED, CREATE THE TAG AT THAT PATH
            if elementTest is None:
                newPath = theRoot.find(oldPath)
                ET.SubElement(newPath,subElement)

        element = treeRoot.find(elementPath) # FIND ALL ELEMENTS AT elementPath FOR EVERYTHING NOT "Theme Keywords (ISO 19115 Topics)" or "Place Keywords (GNIS)".

        # ONCE THE NECESSARY TAG HAS BEEN IDENTIFIED OR CREATED, WRITE DISTINFO VALUES TO WIDGETS
        if k == "Person":
            element.text = distInfoWidgets[0].get()
        elif k == "Organization":
            element.text = distInfoWidgets[1].get()
        elif k == "Address Type":
            element.text = distInfoWidgets[2].get()
        elif k == "Address":
            element.text = distInfoWidgets[3].get()
        elif k == "City":
            element.text = distInfoWidgets[4].get()
        elif k == "State":
            element.text = distInfoWidgets[5].get()
        elif k == "Postal Code":
            element.text = distInfoWidgets[6].get()
        elif k == "Country":
            element.text = distInfoWidgets[7].get()
        elif k == "Email":
            element.text = distInfoWidgets[8].get()

    try:
        metaContact = theRoot.find("metainfo/metc/cntinfo")
        metaContact.clear()
    except:
        pass

    for k,v in metaInfoDict.items():
        elementPath = "."
        #if theRoot.find("./metainfo/metc/cntinfo/cntperp/cntper") is None and theRoot.find("./metainfo/metc/cntinfo/cntorgp/cntorg") is not None:
        for subElement in v:
            oldPath = elementPath
            elementPath+="/"+ subElement

            #ATTEMPT TO FIND THE CURRENT XML TAG AT THE CURRENT ITERATION IN DICTIONARY KEY VALUE
            elementTest =treeRoot.find(elementPath)

            #IF THE XML TAG ISN'T FOUND AT THE PATH SPECIFIED, CREATE THE TAG AT THAT PATH
            if elementTest is None:
                newPath = theRoot.find(oldPath)
                ET.SubElement(newPath,subElement)

            element = treeRoot.find(elementPath)

        if k == "Metadata Date":
            element.text = time.strftime("%Y-%m-%d")
        elif k == "Metadata Author":
            element.text = distInfoWidgets[0].get()
        elif k == "Metadata Organization":
            element.text = distInfoWidgets[1].get()


def select_data_dir():
    global datasets
    global dataDirFrame
    global fileVar

    fileType = fileVar.get()
    print fileType
    datasets=[]

    global idir
    if idir == '':
        idir = cwd

    global dirname
    dirname = askdirectory(initialdir = idir, title = 'Select Data Directory')

    global workspace
    workspace = arcpy.env.workspace = dirname

    for root, dirs, files in os.walk(dirname):
        for file in files:
            if file.endswith(fileType):
                fpath = os.path.join(root,file)
                datasets.append(fpath)

    global num_datasets
    num_datasets = len(datasets)
    """print num_datasets"""
    if num_datasets>0:
        global filesToRead_OK
        filesToRead_OK = True

    if dirname[-1] != '/':
        dirname += '/'

    #CREATES FOLDER IN ORIGINAL DATA DIRECTORY TO STORE TEMPORARY INTERMEDIATE XML FILES
    global tempXMLFiles
    tempXMLFiles = dirname+"tmpXMLFiles"
    if os.path.exists(dirname) > 0 and not os.path.exists(tempXMLFiles):  # ONLY  CREATE THE FOLDER IF IT DOESN'T EXIST ALREADY
        os.makedirs(tempXMLFiles)
        """Made temp Directory"""

    if len(dirname) != 0:

        global preddir_OK
        global outdir_OK
        preddir_OK=True

        global pred_dire
        pred_dire.insert(0, dirname)

        num_datasets_label = Label(dataDirFrame, text=" Found " + str(num_datasets) + " Datasets")
        num_datasets_label.grid(column =1, row = 3, columnspan = 3, sticky=(W))

        if outdir_OK is True and preddir_OK is True:
            global first_window_continue_button
            first_window_continue_button.config(state = "active")

    for widget in second_frame.winfo_children() :
        widget.destroy()

def select_out_dir():
    idir = cwd

    global outdirname
    outdirname = askdirectory(initialdir = idir, title = 'Select Output Directory')

    if outdirname[-1] != '/':
        outdirname += '/'

    if len(outdirname) != 0:
        global preddir_OK
        global outdir_OK
        outdir_OK = True
        if outdir_OK is True and preddir_OK is True:
            global first_window_continue_button
            first_window_continue_button.config(state="active")
            #create_widgets_in_first_frame()

        global out_dir_entry
        out_dir_entry.insert(0, outdirname)

        logFilesNotification_Label = Label(dataDirFrame, text = " Log files will be created in " + str(outdirname))
        logFilesNotification_Label.grid(column = 1, row = 5, sticky = W, columnspan = 3)
        logFilesNotification_Label.config(wraplength = 500)

        # GENERATE LOG FILES SECTION
        currentdate = time.strftime("%Y-%m-%d")
        currenttime = time.strftime("%H.%M")
        modifiedFiles_Log_name = str(outdirname) + "/" + "Files_Modified_" + currentdate + "_" + currenttime + ".txt"
        skippedFiles_Log_name = str(outdirname) + "/" + "Files_Skipped_" + currentdate + "_" + currenttime + ".txt"

        global modifiedFiles_Log
        modifiedFiles_Log = open(modifiedFiles_Log_name, 'a')
        global skippedFiles_Log
        skippedFiles_Log = open(skippedFiles_Log_name, 'a')

        initializationText = "Metadata Editing Session started at " + currenttime + " on " + currentdate + " by " + getpass.getuser() + ".\n"
        modifiedFiles_Log.write(initializationText)
        skippedFiles_Log.write(initializationText)

        modifiedFiles_Log.write("This log file references datasets and associated metadata that have been modified and copied to the output directory.\n")
        skippedFiles_Log.write("This log file references datasets and associated metadata that were not modified nor copied to the output directory.\n")


def ff_scrollbarFunction(event):
    ff_Canvas.configure(scrollregion = ff_Canvas.bbox("all"), width = 750)

def sf_scrollbarFunction(event):
    sf_Canvas.configure(scrollregion=sf_Canvas.bbox("all"))#,width=750, height=780)


""""||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||"""

def create_widgets_in_first_frame():
    ff_rowNum = 0
    #CREATE TITLE"
    title_label = Label(first_frame, text = "METADATA EDITOR TOOL", font = "Helvetica 16 bold")
    title_label.grid(column = 0, row = 0, columnspan = 6, pady = 5,  ipady = 5, ipadx = 20)
    title_label.config(relief=RAISED, bd = 3, bg = "grey", fg = "white", justify = CENTER)
    ff_rowNum+=2

    def launchAboutWindow():
        desc_text ="""This program was created to aid in the creation and editing of metadata for geospatial datasets.  Using the Opengeoporta Metadata Working Groups' General Best Practices Guide (revision January 2015) as a template, 23 metadata categories are offered for editing. Additional support is provided for file renaming practices following the Location_Theme_Date schema advocated by Geomapp.  Currently, the editor will only iterate over shapefiles, though this can easily be changed in the script.  Also, the editor is operating under the assumption that all metadata follows the CSDGM FGDC Schema.  Metadata fields corresponding to ISO 19139 will be mapped in the future.

The editor operates by making a copy of the original xml file into temp folder created in the input data directory.  This is done to preserve the original dataset in the event mistakes or corruption of the file during editing.  Once all necessary metadata as been filled out, the user may proceed to the next file which will copy the original dataset to the output directory and the overwrite the metadata (xml) with the file created in the temp folder.

The editor utilizes the GNIS names system and requries that the user has downloaded the GNIS names index for their state (or nation, though this will take much longer to search) and has built a text file containing a string of comma separated subject field values.  A process step will be written to each xml file indicating the general changes as specified in the first frame.  Should the user wish to change the wording of the process step, please utilize the identifiers ({1}, {2}, {3}, {4}) corresponding to the former name, new name, author, and organization, within the text as the script will try to insert those values at the corresponding location.

Each metadata file will also have the metadata date and contact information updated.  Contact information will only include the Author and Organization, which are pulled from the distributor contact info specified in the first frame, but will replace any metadata contact information which may have previously existed.

Log files created currently only identify the datasets copied and modified\n
            - February 20th, 2015
    \n
    GeoMapp: http://www.geomapp.net/publications_categories.htm#xfr\n
    Opengeoportal Metadata Working Group Best Practices Guide: http://goo.gl/pH09Xn
    """
        aboutWindow = Toplevel(width = 600, height = 100)
        infoMessage = Label(aboutWindow, text = desc_text, padx = 20, pady=20)
        infoMessage.config(wraplength = 550, anchor = W, justify = LEFT)
        infoMessage.pack(side= "top")
        exitWindowButton = Button(aboutWindow,text= "OK", width =20, command = aboutWindow.destroy)
        exitWindowButton.pack(side= "bottom")

    global dataDirFrame
    dataDirFrame = Frame(first_frame)
    dataDirFrame.grid(column = 0, row = ff_rowNum, columnspan =4)

    aboutButton = Button(dataDirFrame, text = "About", width = 15, command = launchAboutWindow)
    aboutButton.grid(column = 0, row = 0, pady =5, padx = 10, sticky = E)

    global fileVar
    fileVar = StringVar()
    fileVar.set(".shp")

    fileOptionLabel = Label(dataDirFrame, text = "Choose File Type:").grid(column = 0, row = 1, pady =5, padx =10, sticky = E)

    shapeOption = Radiobutton(dataDirFrame, text="Shapefiles", variable=fileVar, value=".shp")
    shapeOption.grid(column = 1, row = 1, pady= 5, padx = 10, sticky = W)

    tifOption = Radiobutton(dataDirFrame, text="TIF Files", variable=fileVar, value=".tif")
    tifOption.grid(column = 2, row = 1, pady= 5, padx = 10, sticky = W)

    # CREATE DATA DIRECTORY BUTTON TO IDENTIFY WHERE TO SEARCH
    data_dir_button = Button(dataDirFrame, text = "Select Data Directory", command = select_data_dir)
    data_dir_button.grid(column = 0, row = 2, pady= 5, padx=10, sticky= E)
    global pred_dire
    pred_dire = Entry(dataDirFrame, width = 95)#len(dirname))
    pred_dire.grid(row = 2, column = 1, padx = 5, columnspan = 3, sticky = W)

    #Create Filler
    fillerLabel1 = Label(dataDirFrame)
    fillerLabel1.grid(column = 1, row =3, pady = 3)

    # CREATE OUTPUT DIRECTORY BUTTON TO IDENTIFY WHERE TO WRITE TO
    out_dir_button = Button(dataDirFrame, text = "Select Output Directory", command = select_out_dir)
    out_dir_button.grid(column = 0, row= 4, pady= 5, padx=10, sticky= E)
    global out_dir_entry
    out_dir_entry = Entry(dataDirFrame, width = 95)#(outdirname))
    out_dir_entry.grid(column = 1, row = 4, padx = 5, columnspan = 3, sticky = W)
    ff_rowNum+=1

    fillerLabel2 = Label(dataDirFrame)
    fillerLabel2.grid(column = 1, row = 5, pady = 3)

    defaultInfo_Frame = LabelFrame(first_frame, text = " UNIVERSAL METADATA INFO ")
    defaultInfo_Frame.grid(column = 0, columnspan = 4, row = ff_rowNum, padx = 10, pady = 10, ipadx = 10, ipady = 10, sticky = W)
    defaultInfo_Frame.config(bd = 2, relief = "sunken")
    defInf_row = 0

    distInfo_Frame = LabelFrame(defaultInfo_Frame, text = " Distributor Contact Information ", relief = "groove")
    distInfo_Frame.grid(column =0, columnspan = 2, row = defInf_row, padx = 50, pady = 10, ipadx = 10, ipady = 10, sticky = N)
    distInfo_Frame.config(labelanchor = N)
    distInfo_row = 0

    distPerson_Label = Label(distInfo_Frame,text = "Person")
    distPerson_Label.grid(column =0, row = distInfo_row, padx =5, pady = 1, sticky = E)
    distPerson_Entry = Entry(distInfo_Frame, width = 50)
    distPerson_Entry.grid(column = 1, row = distInfo_row, padx = 5, sticky = W)
    distPerson_Entry.insert(0, "Open Geoportal Manager")
    distInfo_row +=1

    distOrg_Label = Label(distInfo_Frame,text = "Organization")
    distOrg_Label.grid(column =0, row = distInfo_row, padx =5, pady = 1, sticky = E)
    distOrg_Entry = Entry(distInfo_Frame, width = 50)
    distOrg_Entry .grid(column = 1, row = distInfo_row, padx = 5, sticky = W)
    distOrg_Entry.insert(0, "University of Arizona Library")
    distInfo_row +=1

    distAddType_Label = Label(distInfo_Frame,text = "Address Type")
    distAddType_Label.grid(column =0, row = distInfo_row, padx =5, pady = 1, sticky = E)
    distAddType_Entry = Entry(distInfo_Frame, width = 50)
    distAddType_Entry.grid(column = 1, row = distInfo_row, padx = 5, sticky = W)
    distAddType_Entry.insert(0, "physical")
    distInfo_row +=1

    distAddr_Label = Label(distInfo_Frame,text = "Address")
    distAddr_Label.grid(column =0, row = distInfo_row, padx =5, pady = 1, sticky = E)
    distAddr_Entry = Entry(distInfo_Frame, width = 50)
    distAddr_Entry.grid(column = 1, row = distInfo_row, padx = 5, sticky = W)
    distAddr_Entry.insert(0, "1510 E University Blvd.")
    distInfo_row +=1

    distCity_Label = Label(distInfo_Frame,text = "City")
    distCity_Label.grid(column =0, row = distInfo_row, padx =5, pady = 1, sticky = E)
    distCity_Entry = Entry(distInfo_Frame, width = 50)
    distCity_Entry.grid(column = 1, row = distInfo_row, padx = 5, sticky = W)
    distCity_Entry.insert(0, "Tucson")
    distInfo_row +=1

    distState_Label = Label(distInfo_Frame,text = "Arizona")
    distState_Label.grid(column =0, row = distInfo_row, padx =5, pady = 1, sticky = E)
    distState_Entry = Entry(distInfo_Frame, width = 50)
    distState_Entry.grid(column = 1, row = distInfo_row, padx = 5, sticky = W)
    distState_Entry.insert(0, "Arizona")
    distInfo_row +=1

    distZip_Label = Label(distInfo_Frame,text = "Postal Code")
    distZip_Label.grid(column =0, row = distInfo_row, padx =5, pady = 1, sticky = E)
    distZip_Entry = Entry(distInfo_Frame, width = 50)
    distZip_Entry.grid(column = 1, row = distInfo_row, padx = 5, sticky = W)
    distZip_Entry.insert(0, "85712")
    distInfo_row +=1

    distCountry_Label = Label(distInfo_Frame,text = "Country")
    distCountry_Label.grid(column =0, row = distInfo_row, padx =5, pady = 1, sticky = E)
    distCountry_Entry = Entry(distInfo_Frame, width = 50)
    distCountry_Entry.grid(column = 1, row = distInfo_row, padx = 5, sticky = W)
    distCountry_Entry.insert(0, "USA")
    distInfo_row +=1

    distEmail_Label = Label(distInfo_Frame,text = "E-mail")
    distEmail_Label.grid(column =0, row = distInfo_row, padx =5, pady = 1, sticky = E)
    distEmail_Entry = Entry(distInfo_Frame, width = 50)
    distEmail_Entry.grid(column = 1, row = distInfo_row, padx = 5, sticky = W)
    distEmail_Entry.insert(0, "LBRY-uageoportal@email.arizona.edu")
    distInfo_row +=1

    defInf_row +=1

    purpose_Label = Label(defaultInfo_Frame, text = "Purpose")
    purpose_Label.grid(column = 0, row = defInf_row, pady =5, padx = 5, sticky = (S,W))
    defInf_row +=1
    global purpose_Text
    purpose_Text = Text(defaultInfo_Frame, width = 80, height = 4, wrap="word")
    purpose_Text.grid(column = 0, row = defInf_row, padx = 5, sticky = W)
    defaultPurpose = "This datasets is made available to interested persons through the University of Arizona's instance of Open Geoportal.  It has been provided to assist educators, students, researchers, and policy makers in mapping and/or analysis applications."
    purpose_Text.insert(1.0, defaultPurpose)
    defInf_row +=1

    useConst_Label = Label(defaultInfo_Frame, text = "Use Constraints")
    useConst_Label.grid(column = 0, row = defInf_row, pady = 5, padx =5, sticky = (S,W))
    defInf_row +=1
    global useConst_Text
    useConst_Text = Text(defaultInfo_Frame, width =80, height = 4, wrap="word")
    useConst_Text.grid(column = 0, row = defInf_row, padx = 5, sticky =W)
    useConst_Text.insert(1.0,"Not intended for use as a legal description. The University of Arizona does not guarantee the accuracy, completeness, or timeliness of the information provided for download and shall not be liable for any loss or injury resulting from reliance upon the information given.")
    defInf_row +=1

    onlineLoc_Label = Label(defaultInfo_Frame, text = "Online Location")
    onlineLoc_Label.grid(column = 0, row = defInf_row, pady = 5, padx =5, sticky = (S,W))
    defInf_row +=1
    onlineLoc_Text = Text(defaultInfo_Frame, width =40, height = 1)
    onlineLoc_Text.grid(column = 0, row = defInf_row, padx = 5, sticky =W)
    onlineLoc_Text.insert(1.0,"http://geo.library.arizona.edu")
    defInf_row +=1

    author_Label = Label(defaultInfo_Frame, text = "Author (your name)")
    author_Label.grid(column = 0, row = defInf_row, pady = 5, padx = 5, sticky = (S,W))
    defInf_row +=1
    author_Text = Text(defaultInfo_Frame, width =40, height = 1)
    author_Text.grid(column = 0, columnspan = 2, row = defInf_row, padx = 5, sticky = W)
    author_Text.insert(1.0,"Ben Hickson")
    defInf_row +=1

    processStep_Label = Label(defaultInfo_Frame, text = "Process Step Info")
    processStep_Label.grid(column = 0, columnspan = 3, row = defInf_row, padx = 5, pady = 5,sticky =(S,W))
    defInf_row +=1
    processStep_Text = Text(defaultInfo_Frame, width =80, height = 5, wrap="word")
    processStep_Text.grid(column = 0, columnspan = 4, row = defInf_row, padx = 5, sticky = W)

    processText = "Dataset renamed from {1} to {2} by {3} with the {4}.  Metadata fields corresponding the Open Geoportal Working Group Best Practices Guide (http://opengeoportal.org/working-groups/metadata/) were also updated."
    processStep_Text.insert(1.0, processText)
    defInf_row +=1


    global distInfoWidgets
    distInfoWidgets = [distPerson_Entry,distOrg_Entry,distAddType_Entry,distAddr_Entry,distCity_Entry,distState_Entry,distZip_Entry,distCountry_Entry,distEmail_Entry]
    global universalWidgets
    universalWidgets = [onlineLoc_Text,author_Text,processStep_Text,distOrg_Entry]

    processInsert_Label = Label(defaultInfo_Frame, text = "* {1} = Old Dataset Name (will correspond to specific file)\n   {2} = New Dataset Name (will correspond to specific file)\n   {3} = Author Name (global, see above)\n   {4} = Organization (global, see above)")
    processInsert_Label.grid(column = 0, columnspan = 4, row = defInf_row, padx = 5, sticky = W)
    processInsert_Label.config(justify = LEFT, anchor = W)
    defInf_row +=1

    identifierInfo_Label = Label(defaultInfo_Frame, text = "Persistent Unique ID Prefix")
    identifierInfo_Label.grid(column = 0, columnspan = 3, row = defInf_row, padx = 5, pady = 5, sticky = (S,W))
    defInf_row +=1

    global identifierInfo_Text
    identifierInfo_Text = Entry(defaultInfo_Frame, width = 80)
    identifierInfo_Text.grid(column = 0, columnspan = 4, row = defInf_row, padx = 5, sticky = W)
    identifierInfo_Text.insert(0, "10.2458/azu_geo_")
    defInf_row +=1

    ff_rowNum +=1

    # QUIT BUTTON TO EXIT PROGRAM
    first_window_quit_button = Button(first_frame, text = "QUIT", command = quit_program)
    first_window_quit_button.grid(column=2, row = ff_rowNum, pady=10, sticky=(N))

    global first_window_continue_button
    first_window_continue_button = Button(first_frame, text = "CONTINUE", command = call_second_frame_on_top)
    first_window_continue_button.grid(column=3, row=ff_rowNum, pady=10, sticky=(N))
    first_window_continue_button.config(state="disabled") # DON'T ALLOW CONTINUE UNLESS PREDICTORY DIRECTORY AND OUTPUT DIRECTORY ARE SET (outdir_OK == True and preddir_OK == True)

    first_frame.update()
    ff_Maxheight = root_window.winfo_screenheight()
    if ff_Maxheight < 780:
        ff_Canvas.config(height=maxheight-100)
    else:
        ff_Canvas.config(height=780)

    first_frame.bind_class("Text","<Tab>",focus_next_window)

    global preddir_OK
    global outdir_OK
    preddir_OK=False
    outdir_OK=False

def write_widget_values_to_XML(testUpdate):
    global file_rename_Frame
    global puidEntry
    themeKeyCount = 0
    for widget in second_frame.winfo_children():                        # Get a list of all children of second_frame widget
        for k,v in widgetDict.items():                                  # Begin iterating through keys and values of widgetDict (widgetID: element Path)
            parent = v[2]
            if widget.winfo_id() == k:                                  # Test if the widget ID number found in the children list matches a dictionary key value
                if widget.winfo_class() == "Text":                      # Test to see if the widget is of type Text
                    def setValue():
                            widget.config(background="white")
                            parent[v[3]].text = widgetValue   #Write current text in Text widget field to XML tag located at index of parent identified at v[3]

                    widgetValue = widget.get(1.0,"end")
                    widgetValue = widgetValue[0:len(widgetValue)-1]     # NEED TO REMOVE LINE-BREAK VALUE AUTOMATICALLY CONTAINED AT END OF TEXT WIDGET
                    if testUpdate is True:
                        if v[0].find("Publication Date") != -1:  # Check if key value contains "Date"
                            def numCheck(date):
                                try:
                                    int(date)
                                    return True
                                except:
                                    return False

                            year = widgetValue.split("-")[0]
                            try:
                                month = widgetValue.split("-")[1]
                                day = widgetValue.split("-")[2]
                            except:
                                month = ""
                                day = ""

                            if numCheck(year) and len(year) == 4 and int(year) <= int(time.strftime("%Y")) and \
                            numCheck(month) and len(month) == 2 and int(month) >= 1 and int(month) <= 12 and \
                            numCheck(day) and len(day) == 2 and int(day) >= 1 and int(day) <= 31:
                                setValue()
                            elif year.find("Unknown") != -1:
                                setValue
                            else:
                                widget.config(background="red")
                                parent[v[3]].text = ""
                                allFilled = False

                        elif len(widgetValue) > 2:
                            setValue()
                        else:
                            widget.config(bg="red")
                            parent[v[3]].text = ""
                            allFilled = False
                    else:
                        setValue()

                elif widget.winfo_class() == "Menubutton":                      #Test to see if the widget is of type Menubutton
                    if v[0] == "Simple Data Type":                              #Match to Simple Data Type Menu
                        for stringVarIndex in range(len(sdtstypeVars)):
                            menuValue = sdtstypeVars[stringVarIndex].get()      #Get current String Variable for simple data type
                            parent[v[3]].text = menuValue                       #Set the xml element text value to the value found in the string variable
                    elif v[0] == "Data Type":
                        for stringVarIndex in range(len(typesrcVars)):
                            menuValue = typesrcVars[stringVarIndex].get()
                            parent[v[3]].text = menuValue
                    elif v[0] == "Metadata Language":
                        menuValue = metadatalangVar.get()
                        parent[v[3]].text = menuValue
                    elif v[0] == "Access Constraints":
                        menuValue = accessConst_Var.get()
                        selection = re.compile(menuValue + ".*" )
                        menuValue = [m.group(0) for string in accessConstraints for m in [selection.search(string)] if m][0]  # Match the menu value selection to the full description identified in list accessConstraints
                        parent[v[3]].text = menuValue
                    elif v[0] == "Theme Keywords (ISO 19115 Topics)":
                        menuValue = isoTopicCategoryVars[themeKeyCount].get()
                        parent[v[3]].text = menuValue
                        themeKeyCount+=1

                    if len(menuValue) <= 2 and testUpdate is True:
                        widget.config(bg = "red")
                        parent[v[3]].text = ""
                    else:
                        widget.config(bg = "grey")

                elif widget.winfo_class() == "Entry":  # Applies only to Place Keywords (GNIS)
                    widgetValue = widget.get()
                    if len(widgetValue) <= 2 and testUpdate is True:
                        widget.config(background="red")
                        parent[v[3]].text = ""
                        allFilled = False
                    else:
                        widget.config(background="white")
                        parent[v[3]].text = widgetValue

                elif widget.winfo_class() == "Label":
                    parent[v[3]].text = puidEntry
                    """ This attribute is unique to the University of Arizona which is using DOI as the PUI """
                    parent[v[3]].set("PUID","University of Arizona Registered DOI")

    for widget in file_rename_Frame.winfo_children():
        if widget.winfo_class() == "Entry":
            if len(widget.get()) <= 1 and testUpdate is True:
                widget.config(background="red")
            else:
                widget.config(background="white")


def openXMLDoc():
    global originalXMLFile
    if os.path.exists(originalXMLFile):
        webbrowser.open_new_tab(originalXMLFile)
    else:
        issueText = "Unable to locate original XML File at \n\n" + originalXMLFile
        noFileWindow = Toplevel(width = 200, height = 100)
        warningMessage = Label(noFileWindow, text = issueText)
        warningMessage.pack(side= "top")
        exitWindowButton = Button(noFileWindow,text= "OK", width =20, command = noFileWindow.destroy)
        exitWindowButton.pack(side= "bottom")

def insertProcessStep(type):
    global count
    global datasets
    global out_dataset
    global defaultInputValues

    oldName = datasets[count-1].split("\\")[-1]
    newName = out_dataset.split("\\")[-1]
    author = defaultInputValues[1]
    organization = defaultInputValues[3]
    processText = defaultInputValues[2]

    processText = processText.replace("{1}",oldName).replace("{2}",newName).replace("{3}",author).replace("{4}",organization) # Remove numbers identifying variable location for reader from first_frame process text

    if type == "FGDC":
        """ NOTE: POTENTIAL INCOPATIBILITY WITH ISO 19139 """
        parentPath = "./dataqual/lineage"
        parent = treeRoot.find(parentPath)
        ET.SubElement(parent,"procstep")
        for k in list(xmlProcessStep):
            parentPath = "./dataqual/lineage" + "/" + xmlProcessStep[k][2]
            parent = treeRoot.findall(parentPath)[-1]       # SET ELEMENT TO LAST ELEMENT FOUND AT parentPath
            ET.SubElement(parent,xmlProcessStep[k][3])
            elementPath = parentPath + "/" + xmlProcessStep[k][3]
            element = treeRoot.findall(elementPath)[-1]     # SET ELEMENT TO LAST ELEMENT FOUND AT elementPath
            if k == "Process Date":
                element.text = time.strftime("%Y-%m-%d")
            elif k == "Process Time":
                element.text = time.strftime("%H:%M:%S")
            elif k == "Process Description":
                element.text = processText

def createNotificationWindow(issueText):
    def notificationWindowOK():
        global notificationWindow
        notificationWindow.destroy()
        notificationWindow.grab_release()
    # IDENTIFY CURRENT COORDINATES OF ROOT WINDOW AND SPECIFY GEOMETRY/COORDINATES FOR TOPLEVEL WIDGET notificationWindow
    rootGeometry = root_window.winfo_geometry()
    coords = rootGeometry.split("+")[1:3]
    rootWidth = rootGeometry.split("x")[0]
    rootHeight = rootGeometry.split("x")[1].split("+")[0]
    notificationWindow_xoffset = int(coords[0])+(int(rootWidth)/2)-100
    notificationWindow_yoffset = int(coords[1])+(int(rootHeight)/2)-50

    global notificationWindow
    notificationWindow = Toplevel(width = 200, height = 100)
    notificationWindow.geometry("{}x{}+{}+{}".format(300,100,notificationWindow_xoffset,notificationWindow_yoffset))
    notificationWindow.update()
    notificationWindow.grab_set()
    warningMessage = Label(notificationWindow, text = issueText)
    warningMessage.config(wraplength = 300)
    warningMessage.pack(side= "top")
    exitWindowButton = Button(notificationWindow,text= "OK", width =20, command = notificationWindowOK)
    exitWindowButton.pack(side= "bottom")

# FUNCTION THAT WILL RESET ALL WIDGETS IN THE SECOND FRAME
def save_changes_and_copy():

    global allFilled
    global outdirname
    global combineNameSchema
    global fileNameSet
    global metadataType
    global data_type
    global numTextandEntryWidgets
    global fieldFilled
    global count
    global tmpXMLFile
    global modifiedFiles_Log
    global mod_Datasets


    data_type = fileVar.get()
    print data_type

    global out_dataset
    out_dataset = os.path.join(os.path.realpath(outdirname),str(combineNameSchema))
    out_metadatafile = out_dataset + ".xml"

    #THIS SECTION WILL CHECK TO MAKE SURE THAT ALL TEXT AND ENTRY WIDGETS HAVE VALUES BEFORE ALLOWING SAVE AND PROCEEDING TO NEXT FILE
    numTextandEntryWidgets = 0  #SETS COUNT OF NUMBER OF WIDGETS
    fieldFilled = 0             #SETS COUNT OF WIDGTS WITH VALUES

    for widget in second_frame.winfo_children():          #Get a list of all children of second_frame widget
        if widget.winfo_class() == "Text":                #Test to see if the widget is of type Text
            numTextandEntryWidgets += 1       #IDENTIFIED TEXT WIDGET, SO ADD TO WIDGET COUNT
            widgetValue = widget.get(1.0,"end")
            widgetValue = widgetValue[0:len(widgetValue)-1]  #NEED TO REMOVE LINE-BREAK VALUE AUTOMATICALLY CONTAINED AT END OF TEXT WIDGET
            if len(widgetValue) >= 2:
                fieldFilled += 1            #IDENTIFIED TEXT WIDGET VALUE, SO ADD TO WIDGETS WITH VALUE COUNT
    for widget in file_rename_Frame.winfo_children():
        if widget.winfo_class() == "Entry":
            numTextandEntryWidgets += 1       #IDENTIFIED ENTRY WIDGET, SO ADD TO WIDGET COUNT
            widgetValue = widget.get()
            if len(widgetValue) >= 2:
                fieldFilled += 1            #IDENTIFIED ENTRY WIDGET VALUE, SO ADD TO WIDGETS WITH VALUE COUNT

    if numTextandEntryWidgets > 0 and fieldFilled > 0 and fieldFilled == numTextandEntryWidgets and fileNameSet == True:
        allFilled = True  # allFilled SET TO TRUE WHEN ALL TEXT AND ENTRY WIDGETS AND FILE NAME HAVE VALUE.

    if allFilled == True:
        insertProcessStep(metadataType)

         # IF allFilled SET TO TRUE, COPY DATESET TO OUTPUT DIRECTORY AND OVERWRITE XML FILE WITH FILE IN MEMORY
        try:
            arcpy.Copy_management(datasets[count-1], out_dataset)
            modifiedFiles_Log.write(time.strftime("%H:%M") + " - Copying dataset " + datasets[count-1] + "to" + out_dataset + "\n")

            theRoot.write(out_metadatafile)
            modifiedFiles_Log.write(time.strftime("%H:%M") + " - Copying temp xml file to xml file at " + out_metadatafile + "\n")
            # IF allFilled SET TO TRUE, REMOVE ALL WIDGETS FROM SECOND FRAME

            mod_Datasets[datasets[count-1]] = out_dataset

            widgetlist = second_frame.winfo_children()
            for widget in widgetlist:
                widget.destroy()

            os.remove(tmpXMLFile) # Delete intermediate tmpXMLFile created for this dataset

            # IF END OF DATASET LIST IS REACHED IS REACHED, CALL UP THIRD FRAME
            if num_datasets == count:
                call_third_frame_on_top()
            # IF THERE ARE MORE DATASETS IN DATASET LIST, PROCEED TO NEXT FILE
            else:
                create_widgets_in_second_frame()
                allFilled = False

        except:
            issueText = "Unable to Copy Dataset\nPlease SKIP"
            createNotificationWindow(issueText)
            if os.path.exists(out_dataset):   # PROGRAM LIKELY TO FAIL AT EITHER DATASET COPY OR XML WRITE PROCESS.  IF DATASET COPY SUCCEEDS, BUT XML COPY FAILS, REMOVE THE DATASET COPIED FROM OUT FOLDER SO AS TO NOT ADD CONFUSION
                arcpy.Delete_management(out_dataset)

    else:  #IF allFilled IS NOT TRUE, THEN IT HAS BEEN DETERMINED THAT SOME WIDGETS DO NOT HAVE CONTENT AND THE PROGRAM WON'T LET YOU PROCEED
        issueText = "Please ensure that all fields have been filled out and click 'Update Fields' to write new values to the temp XML Metadata File."
        createNotificationWindow(issueText)

def create_widgets_in_second_frame():

    global fileNameSet
    fileNameSet = False
    global combineNameSchema
    combineNameSchema = 0
    global allFilled
    allFilled = False

    def skipDataset():
        global skipped_Datasets
        global skippedFiles_Log

        skippedFiles_Log.write(" Dataset: " + datasets[count-1] + "\n")
        skipped_Datasets.append(datasets[count-1])
        try:
            os.remove(tmpXMLFile)  # Need to do this under the try method in case an xml file was not found, in which case the temp xml file would not have been created.
        except:
            pass
        widgetlist = second_frame.winfo_children()
        for widget in widgetlist :
            widget.destroy()
        create_widgets_in_second_frame()

    # FUNCTION THAT CREATES NEW FILE NAME AND LABEL INDICATING NAME
    def updateXML():
        global puid
        global identifierInfo_Text
        global updateXML_Ran
        global file_rename_Frame
        global new_file_Labe
        global fileNameRow

        fullName = location_Entry.get().replace(" ", "_")+"_"+theme_Entry.get().replace(" ", "_") + "_" + date_Entry.get().replace(" ", "_")
        global puidEntry
        puidEntry = identifierInfo_Text.get() + fullName.lower()
        puid.config(text = puidEntry)

        # RETRIEVE NEW VALUES FROM ALL Text AND MenuButton WIDGETS
        write_widget_values_to_XML(True)

        # NEW FILE NAME SECTION

        global combineNameSchema
        combineNameSchema = fullName + ".tif"   #Needed to convert to lower case because crossref only permits lowercase.  Crossref will be used by UA to register DOI's for a peristent UID
        new_file_Label.config(text=combineNameSchema)
        new_file_Label.grid(column=1,row=3,padx=3,pady=10,sticky=(S,W), columnspan =2)

        if len(combineNameSchema) > 8:
            global fileNameSet
            fileNameSet = True

    global count
    global dirname
    global tempXMLFiles
    global modifiedFiles_Log
    global skippedFiles_Log
    default_text = "No content found in metadata."

    # AS LONG AS THERE IS MORE THAN ONE DATASET, PROCEED WITH
    if len(datasets)>0:
        count +=1

        second_window_label = Label(second_frame, text="Dataset: "+ datasets[count-1],font='bold')
        second_window_label["relief"]="ridge"
        second_window_label.grid(column=0, row=0, pady=10, ipady = 5,ipadx = 5, padx=10, sticky=W, columnspan = 6)

        #IDENTIFY METADATA FILE
        global originalXMLFile
        originalXMLFile = datasets[count-1] + ".xml"            # SET XML FILE LOCATION AND NAME FROM SHAPEFILE INFO.  SUBTRACT ONE TO EQUATE INDEX LOCATION TO LENGTH OF DATASETS LIST

        # TEST FOR EXISTENCE OF XML FILE AND IF FOUND RUN xmlElementsLabels FUNCTION
        if os.path.isfile(originalXMLFile):
            fileFound = True
            # IF XML FILE FOUND FOR DATASET, COPY XML FILE TO TEMP FOLDER AND RUN xmlElementLabels FUNCTION ON TEMP XML FILE
            baseFileName = os.path.basename(originalXMLFile)    # GET DATASET NAME
            global tmpXMLFile
            tmpXMLFile = tempXMLFiles + "/" + baseFileName      # SET TEMP FILE DIRECTORY
            if not os.path.exists(tmpXMLFile):
                shutil.copyfile(originalXMLFile,tmpXMLFile)     # IF IT HASN'T ALREADY BEEN COPIED FROM ON AN EARLIER ITERATION, COPY XML FILE TO TEMP DIRECTORY

            """ IF INTRODUCING ISO 19139 LATER, USE THIS SECTION TO CREATE DETERMINATION OR SELECTION OF METADATA TYPE """
            global metadataType
            metadataType = "FGDC"
            xmlElementsLabels(metadataType,tmpXMLFile)          # RUN FUNCTION THAT WILL CREATE WIDGETS FOR ALL XML ELEMENTS AND FILL THEM WITH CURRENT XML ELEMENT VALUES

            # THIS SECTION SETS THE SIZE OF THE SECOND FRAME CANVAS (sf_Canvas) TO MAKE SURE THAT IT FITS ON THE USERS SCREEN.
            second_frame.update()
            dataset_name_width = second_window_label.winfo_width()
            if dataset_name_width > 750:
                sf_Canvas.config(width = dataset_name_width+50)
            else:
                sf_Canvas.config(width=800)
            sf_MaxHeight = root_window.winfo_screenheight()
            if sf_MaxHeight < 780:
                sf_Canvas.config(height=sf_MaxHeight-100)
            else:
                sf_Canvas.config(height=780)
        else:
            fileFound = False
            rowNum = 2
            no_XML_File_Label = Label(second_frame, text = "Unable to find XML metadata file for this dataset. Please skip",background='red',foreground='white')
            no_XML_File_Label.grid(column = 1, columnspan = 4, row = rowNum, pady=10)
            rowNum+=1

        global rowNum
        if fileFound is True:
            global file_rename_Frame
            file_rename_Frame = LabelFrame(second_frame, text = " - File Renaming Section - ")
            file_rename_Frame.grid(column = 0, row = rowNum, columnspan = 6, pady = 10, ipadx = 10, ipady = 10)
            file_rename_Frame.config(bd = 1)
            rowNum+= 1

            location_label = Label(file_rename_Frame,text="Location")
            location_label.grid(column = 0, row = 1, pady = 3, padx = 3, sticky = (S,E))
            theme_label = Label(file_rename_Frame, text = "Theme")
            theme_label.grid(column = 1, row = 1, pady = 3, padx = 3, sticky = S)
            date_label = Label(file_rename_Frame, text = "Date (Format: YYYY)")
            date_label.grid(column = 2, row = 1, pady = 3, padx = 3, sticky = (S,W))

            location_Entry= Entry(file_rename_Frame)
            location_Entry.grid(column =0, row= 2, pady=3, padx=3,sticky=(S,E))
            theme_Entry = Entry(file_rename_Frame)
            theme_Entry.grid(column =1, row= 2, pady=3, padx=3,sticky=S)
            date_Entry = Entry(file_rename_Frame)
            date_Entry.grid(column =2, row= 2, pady=3, padx=3,sticky=(S,W))

            new_file_name_Label = Label(file_rename_Frame, text="New File Name: ")
            new_file_name_Label.grid(column =0, row= 3, padx= 3, pady= 10,sticky=(S,E))

            new_file_Label = Label(file_rename_Frame,text="__.tif", background = 'white',relief='groove',font='bold')
            new_file_Label.grid(column=1,row=3,padx=3,pady=10,sticky=(S,W), columnspan =2)

##            identifier_Label = Label(second_frame, text = "Persistent Identifier: ")
##            identifier_Label.grid(column =0, row= rowNum, padx= 3, pady= 10, sticky = (S,E))
##
##            identifier = Label(second_frame, text = "", background = 'white',relief='groove',font='bold')
##            identifier.grid(column=1, row=rowNum, columnspan = 3, padx=3, pady=10, sticky = (S,W))
##            rowNum+= 1

            # UPDATE BUTTON FOR FILE NAMING
            update_Button = Button(second_frame,text = "Update Fields", command=updateXML)
            update_Button.grid(row= rowNum, column= 3, columnspan = 2, sticky= E)
            rowNum+= 1


    # Create Open XML Document Button for second_frame
    second_window_openXML_button = Button(second_frame, text = "Open Original XML Doc", command = openXMLDoc)
    second_window_openXML_button.grid(column = 0, row= rowNum, pady=10, padx=10, sticky=S)

    bottom_second_frame = Frame(second_frame)
    bottom_second_frame.grid(row=rowNum,column=4, sticky=E)
    rowNum+=1

    # Create the Next buttons for second_frame (depending on end of file list or not will change behavior)
    if count == num_datasets:
        # Create Skip button for second_frame
        second_window_next_button = Button(bottom_second_frame, text = "FINISH", command = save_changes_and_copy) #Moves to third and final frame
        second_window_next_button.pack(side=RIGHT,pady=3,padx=3)

        def finalSKIP():
            global skipped_Datasets
            global skippedFiles_Log

            skippedFiles_Log.write("Dataset: " + datasets[count-1] + "\n")
            skipped_Datasets.append(datasets[count-1])

            call_third_frame_on_top()

        second_window_skip_button = Button(bottom_second_frame, text = "SKIP", command = finalSKIP)
        second_window_skip_button.pack(side=RIGHT,pady=3,padx=3)

    else:
        # Create Skip button for second_frame
        second_window_next_button = Button(bottom_second_frame, text = "NEXT", command = save_changes_and_copy) #Resets second frame
        second_window_next_button.pack(side=RIGHT,pady=3,padx=3)

        second_window_skip_button = Button(bottom_second_frame, text = "SKIP", command = skipDataset)
        second_window_skip_button.pack(side=RIGHT,pady=3,padx=3)

    # Create the Quit button for second_frame
    second_window_quit_button = Button(bottom_second_frame, text = "QUIT", command = quit_program)
    second_window_quit_button.pack(side=RIGHT,pady=3,padx=3)

    dataset_count_label = Label(second_frame,text="DATASET "+str(count)+ " OF " +str(num_datasets))
    dataset_count_label.grid(row= rowNum, column = 3, columnspan = 2,pady=10,sticky=E)

def create_widgets_in_third_frame():
    global mod_Datasets
    def OnTopScroll(*args):
        left_Listbox.yview(*args)
        right_Listbox.yview(*args)

    def OnBottomScroll(*args):
        bottom_Listbox.yview(*args)


    title_Label = Label(third_frame_master, text = "SESSION SUMMARY", relief = GROOVE)
    title_Label.grid(column = 0, row = 0, columnspan = 2, padx = 10, pady = 10, ipadx = 5, ipady = 5)

    previousTitle_Label = Label(third_frame_master,text = "Input Dataset")
    previousTitle_Label.grid(column = 0, row = 3)

    newTitle_Label = Label(third_frame_master,text = "Modified Dataset")
    newTitle_Label.grid(column = 1, row = 3)

    top_Frame = Frame(third_frame_master)#, padx = 10, pady = 10)
    top_Frame.grid(column = 0, row = 4, columnspan = 2, padx = 5, pady = 5, sticky = (W,N,E))#pack(side = "top", padx = 15, pady = 15)

    skippedTitle_Label = Label(third_frame_master, text = "\nSkipped Datasets")
    skippedTitle_Label.grid(column = 0, row = 5, rowspan = 2, columnspan = 2)

    bottom_Frame = Frame(third_frame_master)
    bottom_Frame.grid(column = 0, row = 7, columnspan = 2, padx = 5, pady = 5, sticky = (W,N,E))#pack(side = "bottom", padx = 15, pady = 15)

    exit_button = Button(third_frame_master, text = "EXIT", command = quit_program)
    exit_button.grid(column = 1, row = 8, pady = 10, ipadx = 5, ipady = 5, sticky = (S,E))

    top_Scrollbar = Scrollbar(top_Frame, orient="vertical", command=OnTopScroll)
    left_Listbox = Listbox(top_Frame, width = 60, height = 20, yscrollcommand=top_Scrollbar.set)
    right_Listbox = Listbox(top_Frame, width = 60, height = 20, yscrollcommand=top_Scrollbar.set)
    top_Scrollbar.pack(side="right",fill="y")
    left_Listbox.pack(side="left", expand=True)
    right_Listbox.pack(side="right", expand=True)

    bottom_Scrollbar = Scrollbar(bottom_Frame, orient = "vertical", command = OnBottomScroll)
    bottom_Listbox = Listbox(bottom_Frame, width = 120, height = 15, yscrollcommand = bottom_Scrollbar.set)
    bottom_Scrollbar.pack(side = "right", fill = "y")
    bottom_Listbox.pack(side = "bottom", expand = True)

    for k,v in mod_Datasets.items():
        left_Listbox.insert(END, k)
        right_Listbox.insert(END,v)

    for item in skipped_Datasets:
        bottom_Listbox.insert(END, item)


""""||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||"""

def call_first_frame_on_top():
    second_frame_master.grid_forget()
    first_frame_master.grid(column=0, row=0, padx=20, pady=5, sticky=(W, N, E))

def call_second_frame_on_top():
    global dirname
    global outdirname
    global datasets
    global modifiedFiles_Log
    global skippedFiles_Log
    global universalWidgets

    global defaultInputValues
    defaultInputValues = []

    for widget in universalWidgets:
        if widget.winfo_class() == "Text":
            widgetValue = widget.get(1.0,"end")[0:-1]   # THE LAST INDEX POSITION OF THE TEXT WIDGETS IS A LINE BREAK, DON'T WANT THAT
            defaultInputValues.append(widgetValue)      # Builds widget values into list in the same order as the widgets in universalWidgets list
        elif widget.winfo_class() == "Entry":
            widgetValue = widget.get()
            defaultInputValues.append(widgetValue)

    modifiedFiles_Log.write("Input Directory : " + dirname + "\nOutput Directory : " + outdirname + "\nTotal Number of Datasets in Input Directory : " + str(len(datasets)) + "\n\n")
    skippedFiles_Log.write("Input Directory : " + dirname + "\nOutput Directory : " + outdirname + "\nTotal Datasets in Input Directory : " + str(len(datasets)) + "\n\n")

    first_frame_master.grid_forget()
    create_widgets_in_second_frame()
    second_frame_master.grid(column=0, row=0, padx=20, pady=5, sticky=(W,N,E))

def call_third_frame_on_top():
    global modifiedFiles_Log
    global skippedFiles_Log

    modifiedFiles_Log.write("\n\n...Reached end of file list.  Closing log file.")
    modifiedFiles_Log.close()

    skippedFiles_Log.write("\n\n...Reached end of file list.  Closing log file.")
    skippedFiles_Log.close()

    second_frame_master.grid_forget()
    create_widgets_in_third_frame()
    third_frame_master.grid(column=0, row=0, padx=20, pady=5, sticky=(W, N, E))

def quit_program():
    global tmpXMLFile
    global modifiedFiles_Log
    global skippedFiles_Log

    root_window.destroy()
    try:
        modifiedFiles_Log.close()
        skippedFiles_Log.close()
    except:
        pass
    try:
        os.remove(tmpXMLFile)  # Need to use try method in case the temp xml file was never created.
    except:
        pass

###############################
# Main program
###############################

# Create the root GUI window.
root_window = Tk()
root_window.wm_title("Metadata Editor Tool")

# Define window size
window_width = 850
window_height= 800

root_window.geometry('{}x{}+{}+{}'.format(window_width,window_height,50,50))

first_frame_master= Frame(root_window)#, width=window_width, height=window_height)
first_frame_master['borderwidth'] = 2
first_frame_master['relief'] = 'sunken'
first_frame_master.grid(column=0, row=0, padx=20, pady=5, sticky=(W,N,E))

ff_Canvas = Canvas(first_frame_master)
first_frame = Frame(ff_Canvas)

ff_Scrollbar = Scrollbar(first_frame_master,orient="vertical",command=ff_Canvas.yview)
ff_Canvas.configure(yscrollcommand=ff_Scrollbar.set)
ff_Scrollbar.pack(side="right",fill="y")
ff_Canvas.pack(side="left", fill = "both")
ff_Canvas.create_window((0,0), window=first_frame, anchor='nw', width = 800)#, anchor='nw')
ff_Canvas.configure(scrollregion=ff_Canvas.bbox("all"))
first_frame.bind("<Configure>",ff_scrollbarFunction)

second_frame_master = Frame(root_window)#, width=window_width, height=window_height)
second_frame_master['borderwidth'] = 2
second_frame_master['relief'] = 'sunken'

# CREATE CANVAS TO SET SCROLLBAR INTO
sf_Canvas = Canvas(second_frame_master)
second_frame = Frame(sf_Canvas)

sf_Scrollbar = Scrollbar(second_frame_master,orient="vertical",command=sf_Canvas.yview)
sf_Canvas.configure(yscrollcommand=sf_Scrollbar.set)
sf_Scrollbar.pack(side="right",fill="y")
sf_Canvas.pack(side="left", fill = "both")
sf_Canvas.create_window((0,0), window=second_frame, anchor='nw')#, width = 800, anchor='nw')
sf_Canvas.configure(scrollregion=sf_Canvas.bbox("all"))
second_frame.bind("<Configure>",sf_scrollbarFunction)


third_frame_master = Frame(root_window, width=window_width, height=window_height)
third_frame_master['borderwidth'] = 2
third_frame_master['relief'] = 'sunken'
third_frame_master.grid(column=0, row=0, padx=20, pady=5, sticky=(W, N, E))

create_widgets_in_first_frame()

# Hide all frames in reverse order, but leave first frame visible (unhidden).
third_frame_master.grid_forget()
second_frame_master.grid_forget()

root_window.mainloop()