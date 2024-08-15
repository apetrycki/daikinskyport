# daikinskyport
API and [Home Assistant](https://www.home-assistant.io/) component for accessing a [Daikin One+ Smart Thermostat](https://daikinone.com/) or [Daikin One Lite](https://www.daikinac.com/content/residential/residential-controllers/daikin-one-lite).

Most functions are supported.  Now welcoming feedback for features and bugs.  This was mostly taken from the ecobee code and modified.

## Installation

This component can be installed via the [Home Assistant Community Store (HACS)](https://hacs.xyz/) or manually.

This integration now requires Home Assistant version 2024.02 or later due to changes made in that version that are not backward compatible.

### Install via HACS

_HACS must be [installed](https://hacs.xyz/docs/installation/prerequisites) before following these steps._

1. Log into your Home Assistant instance and open HACS via the sidebar on the left
2. In the HACS menu, open **Integrations**
3. On the integrations page, select the "vertical dots" icon in the top-right corner, and select **Custom respositories**
4. Paste `https://github.com/apetrycki/daikinskyport` into the **Repository** field and select **Integration** in the **Category** menu
5. Click **ADD**
6. Click **+ EXPLORE & DOWNLOAD REPOSITORIES**
7. Select **Daikin Skyport** and click the **DOWNLOAD** button
8. Click **DOWNLOAD**
9. Restart Home Assistant Core via the Home Assistant console by navigating to **Supervisor** in the sidebar on the left, selecting the **System** tab, and clicking **Restart Core**. A restart is necessary in order to load the component.

### Manual Install

_A manual installation is more risky than installation via HACS. You must be familiar with how to SSH into Home Assistant and working in the Linux shell to perform these steps._

1. Download or clone the component's repository by selecting the **Code** button on the [component's GitHub page](https://github.com/apetrycki/daikinskyport).
2. If you downloaded the component as a zip file, extract the file.
3. Copy the `custom_components/daikinskyport` folder from the repository to your Home Assistant `custom_components` folder. Once done, the full path to the component in Home Assistant should be `/config/custom_components/daikinskyport`. The `__init__.py` file (along with the rest of the files) should be directly in the `daikinskyport` folder.

## Usage

In order for this component to talk with your thermostat, the thermostat must be registered with your online Daikin account. If you haven't already done so, follow the instructions for pairing with the mobile app in the [Daikin documentation](https://backend.daikincomfort.com/docs/default-source/product-documents/residential-accessories/other/hg-one-st.pdf?sfvrsn=c0692726_38).

After pairing the thermostat and installing the component, activate the component by going to **Settings**, **Devices & Services**, **Add Integration**, and searching for Daikin Skyport.  Enter your email and password at the prompt and optionally a name for your account.

The email and password must be the same ones that you used when you created your account in the mobile app.


Once Core has restarted, navigate to **Configuration** in the sidebar, then **Entities**. Use the search box to search for the name of your thermostat. For example, search for `main room` (the name of your thermostat is shown on the touch screen). You should see a `climate`, `weather`, and a number of `sensor` entities.

**NOTE:** This component does not show up in the list of Home Assistant integrations.
