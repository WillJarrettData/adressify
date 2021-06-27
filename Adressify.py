###
### Welcome to the fun address aggregator V0-3
###

#to run this code yourself, you will need to install python and the libraries below
#then type the following in the command line:
#streamlit run "FILEPATH FOR PYTHON FILE HERE"

#Import modules
import pandas as pd
import streamlit as st

import os
import requests
import time

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

pd.set_option('display.max_columns', None)

###
### Set up page 
###

#remove padding
st.markdown(f""" <style>
    .reportview-container .main .block-container{{
        padding-top: 0rem;
        padding-bottom: 0rem;
    }} </style> """, unsafe_allow_html=True)

#Hide streamlit sign
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 

#this is the title
st.title('Enter a New York City address')
#these are the columns
left_column, right_column = st.beta_columns([6,1])
address = left_column.text_input("")
address = address + " new york"
#this is the button
right_column.text('')
right_column.text('')
pressed = right_column.button('Search')

###
### if button is pressed, do the below...
###

if pressed:
    try:
        ###
        ### Ping google API with required address
        ###

        #create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        #print update
        progress_bar.progress(10)
        status_text.text('Pinging Google Geocoding API...')

        #set url and api key
        #if you want to run this code yourself,
        #you will need to change this to:
        #api_key = "[NAME_OF_YOUR_API_HERE]"
        #you can get an api key for yourself here: https://developers.google.com/maps/documentation/geocoding/get-api-key
        #I have hidden my api key as an environmental variable so that I
        #don't get charged for use if the code ends up in the wider world.
        api_key = os.environ.get('GOOGLE_GEO_API')
        url = 'https://maps.googleapis.com/maps/api/geocode/json'
        keys = {'address': address, 'key': api_key}

        #ping the google geocoding api
        r = requests.get(url,params=keys)
        result_dic = r.json()

        ###
        ### Put results into a nice tidy dictionary
        ###

        #define full address
        address = result_dic['results'][0]['formatted_address']
        #define street number
        street_number = "N/A"
        for i in result_dic['results'][0]['address_components']:
            if i['types'][0] == "street_number":
                street_number = i['long_name']
        #define street name
        street_name = "N/A"
        for i in result_dic['results'][0]['address_components']:
            if i['types'][0] == "route":
                street_name = i['long_name']
        #define neighborhood
        neighborhood = "N/A"
        for i in result_dic['results'][0]['address_components']:
            if i['types'][0] == "neighborhood":
                neighborhood = i['long_name']
        #define county
        county = "N/A"
        for i in result_dic['results'][0]['address_components']:
            for j in i['types']:
                if j == "sublocality_level_1":
                    county = i['long_name']
        #define zip code
        _zip = "N/A"
        for i in result_dic['results'][0]['address_components']:
            if i['types'][0] == "postal_code":
                _zip = i['long_name']
        #define coordinates
        lat = result_dic['results'][0]['geometry']['location']['lat']
        lng = result_dic['results'][0]['geometry']['location']['lng']
                    
        #put everything in a dictionary 
        address_dict = {
            'address': address,
            'street_number': street_number,
            'street_name': street_name,
            'neighborhood': neighborhood,
            'county': county,
            'zip': _zip,
            'latitude': lat,
            'longitude': lng
        }
        df = pd.DataFrame([address_dict])

        ###
        ### Grab building records with Selenium 
        ###

        #print update
        progress_bar.progress(35)
        status_text.text('Grabbing building records...')

        #set driver options (to hide the new chrome tab)
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")

        chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")

        #launch driver
        driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)
        #send driver to building records website
        url = "https://a810-dobnow.nyc.gov/publish/Index.html#!/"
        driver.get(url)
        
        #wait until the page loads
        try:
            element = WebDriverWait(driver, 100).until(
                EC.invisibility_of_element_located((By.ID, "veil"))
            )
        except:
            pass

        #input street number
        street_number_input = driver.find_element_by_id('housenumber')
        street_number_input.send_keys(address_dict['street_number'])
        #input street name
        street_name_input = driver.find_element_by_id('streetnumber')
        street_name_input.send_keys(address_dict['street_name'])
        #input borough
        select = Select(driver.find_element_by_id('sel1'))
        select.select_by_visible_text(address_dict['county'])

        #click search
        button = driver.find_element_by_xpath("/html/body/div[1]/div[1]/div[2]/div[4]/div[4]/div[2]/div[2]/div[2]/div[1]/uib-accordion/div/div[1]/div[2]/div/div/div[4]/button")
        button.click()

        #wait until the page loads
        try:
            element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[1]/div[2]/div[4]/div[2]/div[1]/span[3]"))
                )
        except:
            pass

        #grab results
        BIN = driver.find_elements_by_class_name("pad-15")[2].text.replace('BIN# ','')
        record_url = f"http://a810-bisweb.nyc.gov/bisweb/PropertyProfileOverviewServlet?bin={BIN}"
        block = driver.find_elements_by_class_name('form-group')[3].text.replace('Tax Block\n','')
        lot = driver.find_elements_by_class_name('form-group')[4].text.replace('Tax Lot\n','')
        community_board = driver.find_elements_by_class_name('form-group')[5].text.replace('Community Board\n','')
        buildings_on_lot = driver.find_elements_by_class_name('form-group')[7].text.replace('Buildings on Lot\n','')
        health_area = driver.find_elements_by_class_name('form-group')[9].text.replace('Health Area\n','')
        census_tract = driver.find_elements_by_class_name('form-group')[10].text.replace('Census Tract\n','')
        city_owned = driver.find_elements_by_class_name('form-group')[22].text.replace('City Owned\n','')
        tidal_wetlands = driver.find_elements_by_class_name('col-xs-4')[1].text
        freshwater_wetlands = driver.find_elements_by_class_name('col-xs-4')[2].text
        coastal_erosion = driver.find_elements_by_class_name('col-xs-4')[3].text
        special_flood_hazard = driver.find_elements_by_class_name('col-xs-4')[4].text
        tax_building_type = driver.find_elements_by_class_name('col-xs-4')[5].text

        driver.quit()

        ###
        ### Grab financial records with Selenium
        ###

        #print update
        progress_bar.progress(65)
        status_text.text('Grabbing financial records...')

        if address_dict['county'] == "Manhattan":
            borough_selector = "(1) Manhattan"
        elif address_dict['county'] == "Bronx":
            borough_selector = "(2) Bronx"
        elif address_dict['county'] == "Brooklyn":
            borough_selector = "(3) Brooklyn"
        elif address_dict['county'] == "Queens":
            borough_selector = "(4) Queens"
        elif address_dict['county'] == "Staten Island":
            borough_selector = "(5) Staten Island"
        else:
            print("Oh dear, that seems to have broken.")

        #launch webdriver
        driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)
        #send driver to finance website
        url = "https://a836-pts-access.nyc.gov/care/search/commonsearch.aspx?mode=persprop"
        driver.get(url)
        #accept terms + conditions
        button = driver.find_element_by_id("btAgree")
        button.click()

        #wait for page to load
        time.sleep(1)

        #input borough
        select = Select(driver.find_element_by_class_name('FormText'))
        select.select_by_visible_text(borough_selector)
        #input block
        block_input = driver.find_element_by_id('inpTag')
        block_input.send_keys(block)
        #input lot
        lot_input = driver.find_element_by_id('inpStat')
        lot_input.send_keys(lot)
        #click search button
        button = driver.find_element_by_id("btSearch")
        button.click()
        #click link for recent financial transactions
        button = driver.find_element_by_xpath("/html/body/div/div[3]/div/nav/div/div/li[12]")
        button.click()

        #print update
        progress_bar.progress(80)
        status_text.text('Bringing everything together...')

        #waiting for page to load
        try:
            element = WebDriverWait(driver, 100).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div/div[3]/div/nav/div/div/li[12]"))
                )
        except:
            pass

        #grabbing fun financial data
        owner = driver.find_elements_by_class_name("DataletData")[3].text
        land_area_sqft = driver.find_elements_by_class_name("DataletData")[15].text.replace(',','')
        estimated_market_value = driver.find_elements_by_class_name("DataletData")[27].text

        driver.quit()

        #define 'any_flood_risk' variable
        if tidal_wetlands == "No" and freshwater_wetlands == "No" and coastal_erosion == "No" and special_flood_hazard == "No":
            any_flood_risk = "No"
        else:
            any_flood_risk = "Yes"
        
        #convert square feet into acres
        land_area_acres = round(int(land_area_sqft) / 43560, 3)

        #stick everything in a dictionary
        address_dict = {
            'address': address,
            'street_number': street_number,
            'street_name': street_name,
            'neighborhood': neighborhood,
            'county': county,
            'zip': _zip,
            'latitude': lat,
            'longitude': lng,
            'BIN': BIN,
            'record_url': record_url,
            'block': block,
            'lot': lot,
            'community_board': community_board,
            'buildings_on_lot': buildings_on_lot,
            'health_area': health_area,
            'census_tract': census_tract,
            'city_owned': city_owned,
            'record_url': record_url,
            'tidal_wetlands': tidal_wetlands,
            'freshwater_wetlands': freshwater_wetlands,
            'coastal_erosion': coastal_erosion,
            'special_flood_hazard': special_flood_hazard,
            'any_flood_risk': any_flood_risk,
            'tax_building_type': tax_building_type,
            'owner': owner,
            'land_area_sqft': land_area_sqft,
            'land_area_acres': land_area_acres,
            'estimated_market_value': estimated_market_value
            }

        #save as a big lovely dataframe
        df = pd.DataFrame([address_dict])

        #print update
        progress_bar.progress(100)
        status_text.text('')

        #print out results
        st.write(f"**Full address**: {address_dict['address']}")
        st.write(f"**Owner**: {address_dict['owner']}")
        st.write(f"**Estimated market value**: ${address_dict['estimated_market_value']}")
        st.write(f"**Tax code**: {address_dict['tax_building_type']}")
        st.write(f"**Land area (acres)**: {address_dict['land_area_acres']}")
        st.write(f"**Any flood risk**: {address_dict['any_flood_risk']}")
        st.write(f"**Coordinates**: {address_dict['longitude']}, {address_dict['latitude']}")
        st.write(f"**Building record URL**: [Click here for details]({address_dict['record_url']})")

        ###
        ### Put it on a map
        ###

        dfMap = df[["latitude", "longitude"]]
        st.map(dfMap, zoom=11)

    except:
        #error message to display if anything above breaks
        st.write("Hmm, that didn't work. Are you sure that was an NYC address?")
        #reset progress bar
        progress_bar.progress(0)
        status_text.text('')