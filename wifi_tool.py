import base64
import requests
import folium
from folium.plugins import HeatMap
import pandas as pd
import streamlit as st
from winreg import OpenKey, EnumKey, EnumValue, HKEY_LOCAL_MACHINE, CloseKey
import streamlit.components.v1 as components

def val2addr(val):
    if val:
        addr = ""
        for char in val:
            try:
                addr += ("%02x " % ord(char))
            except:
                addr += ("%02x " % ord(chr(char)))
        addr = addr.strip(" ").replace(" ", ":")[:17]
        return True, addr
    else:
        addr = "No data found for this network"
        return False, addr

def get_WIFIs():
    wlans = r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\NetworkList\Signatures\Unmanaged'
    key = OpenKey(HKEY_LOCAL_MACHINE, wlans)
    data = []
    for i in range(1000000):
        try:
            attempt = EnumKey(key, i)
            wlan_key = OpenKey(key, str(attempt))
            _, addr, _ = EnumValue(wlan_key, 5)
            _, name, _ = EnumValue(wlan_key, 4)
            res, mac_address = val2addr(addr)
            wlan_name = str(name)
            data.append({'Network Name': wlan_name, 'MAC Address': mac_address})
            CloseKey(wlan_key)
        except Exception as e:
            break
    return pd.DataFrame(data)

def get_coordinates(mac_address):
    api_user = 'AIDc3e5d1a2cad617367ae2f0a70ee89470'
    api_key = '5b2e0871a4ee135635a20466f2881e15'
    credentials = f'{api_user}:{api_key}'
    b64_credentials = base64.b64encode(credentials.encode()).decode()

    url = 'https://api.wigle.net/api/v2/network/search'
    headers = {
        'Authorization': f'Basic {b64_credentials}'
    }
    params = {
        'netid': mac_address,
        'country': 'IN'
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        if 'results' in data and len(data['results']) > 0:
            first_result = data['results'][0]
            return (first_result['trilat'], first_result['trilong'],
                    first_result.get('rssi', 'No data'),
                    first_result.get('frequency', 'No data'))
        else:
            return None
    else:
        st.error(f"Error fetching data from WIGLE API: {response.status_code}")
        return None

def generate_map(df):
    m = folium.Map(location=[30.7333, 76.7794], zoom_start=12)
    heat_data = []

    for index, row in df.iterrows():
        mac_address = row['MAC Address']
        coords = get_coordinates(mac_address)
        if coords:
            lat, lon, rssi, freq = coords
            location = [lat, lon]
            popup_content = f"{row['Network Name']}<br>Signal Strength: {rssi}<br>Frequency: {freq}"
            heat_data.append(location)
        else:
            location = [30.7333, 76.7794]
            popup_content = row['Network Name']
        
        folium.Marker(location, popup=popup_content).add_to(m)
    
    if heat_data:
        HeatMap(heat_data).add_to(m)
    
    # Save map to HTML and read it
    map_html = 'map.html'
    m.save(map_html)
    return map_html

def main():
    st.title("WiFi Networks Analysis Tool")
    st.write("This tool reads WiFi activity data and provides analysis.")
    
    st.write("Fetching data...")
    wifi_df = get_WIFIs()
    
    if not wifi_df.empty:
        st.write("Data fetched successfully!")
        st.write(wifi_df)
        
        st.write("Generating map...")
        map_html = generate_map(wifi_df)
        
        # Read and display map HTML
        with open(map_html, 'r') as f:
            map_html_data = f.read()
        
        components.html(map_html_data, height=600)
    else:
        st.write("No WiFi data found.")

if __name__ == "__main__":
    main()
