from bs4 import BeautifulSoup
from collections import OrderedDict

import logging
import re


class FacebookSoupParser:

    def parse_about_page(self, content):
        """Extract information from the mobile version of the about page.

        Returns an OrderedDict([('Name', ''), ...]).

        Keys are added only if the fields were found in the about page.

        >>> FacebookSoupParser().parse_about_page('''
        ...    <title id="pageTitle">Mark Zuckerberg</title>
        ... ''')["Name"]
        'Mark Zuckerberg'
        >>> FacebookSoupParser().parse_about_page('''
        ...    <div class="timeline aboutme">
        ...         <div class="dc dd dq" title="Birthday">
        ...             <div class="dv">14 May 1984</div>
        ...         </div>
        ...    </div>
        ...    ''')["Birthday"]
        '14 May 1984'
        >>> FacebookSoupParser().parse_about_page('''
        ...    <div class="timeline aboutme">
        ...         <div class="dc dd dq" title="Birthday">
        ...             <div class="dv">14 May 1984</div>
        ...         </div>
        ...    </div>
        ...    ''')["Year of birth"]
        1984
        >>> FacebookSoupParser().parse_about_page('''
        ...    <div class="timeline aboutme">
        ...         <div class="dc dd dq" title="Birthday">
        ...             <div class="dv">14 May</div>
        ...         </div>
        ...    </div>
        ...    ''')["Day and month of birth"]
        '14 May'
        >>> FacebookSoupParser().parse_about_page('''
        ...    <div class="timeline aboutme">
        ...         <div class="_5cds _2lcw _5cdu" title="Gender">
        ...             <div class="_5cdv r">Male</div>
        ...         </div>
        ...    </div>
        ...    ''')["Gender"]
        'Male'
        >>> FacebookSoupParser().parse_about_page('''
        ...    <div class="timeline aboutme">
        ...         <div id="relationship"><div class="cq">''' + \
                    'Relationship</div><div class="cu do cv">' + \
                    'Married to <a class="bu" href="/someone">Someone</a>' + \
                    ' since 14 March 2010</div></div>' + '''
        ...    </div>
        ...    ''')["Relationship"]
        'Married'
        >>> FacebookSoupParser().parse_about_page('''
        ...    <div class="timeline aboutme">
        ...         <div id="work">
        ...             <a class="bm" href="">
        ...                 <img src="" alt="1st work">
        ...             </a>
        ...             <a class="bm" href="">
        ...                 <img src="" alt="2nd work">
        ...             </a>
        ...         </div>
        ...    </div>''')["Work"]
        '1st work'
        >>> FacebookSoupParser().parse_about_page('''
        ...    <div class="timeline aboutme">
        ...         <div id="education">
        ...             <a class="bm" href="">
        ...                 <img src="" alt="1st education">
        ...             </a>
        ...             <a class="bm" href="">
        ...                 <img src="" alt="2nd education">
        ...             </a>
        ...         </div>
        ...    </div>''')["Education"]
        '1st education'
        >>> len(FacebookSoupParser().parse_about_page(""))
        0
        """
        soup = BeautifulSoup(content, "lxml")

        user_info = OrderedDict()

        name_tag = soup.find("title")
        if name_tag:
            user_info["Name"] = name_tag.text

        tags = [
            'AIM', 'Address', 'BBM', 'Birth Name', 'Birthday',
            'Facebook', 'Foursquare', 'Gadu-Gadu', 'Gender', 'ICQ',
            'Instagram', 'Interested in', 'Languages', 'LinkedIn',
            'Maiden Name', 'Mobile', 'Nickname', 'Political Views',
            'Religious views', 'Skype', 'Snapchat', 'Twitter', 'VK',
            'Websites', 'Windows Live Messenger', 'Year of birth']

        for tag in tags:
            found_tag = soup.find("div", attrs={"title": tag})
            if found_tag:
                user_info[tag] = found_tag.text. \
                    replace(tag, "").replace("\n", "")

        if "Birthday" in user_info:
            parsed_birthday = user_info["Birthday"]
            if parsed_birthday.count(" ") != 2:
                user_info["Day and month of birth"] = parsed_birthday
                del user_info["Birthday"]
            else:
                user_info["Day and month of birth"] = " ".join(
                    parsed_birthday.split(" ")[0:2])
                user_info["Year of birth"] = parsed_birthday.split(" ")[-1]

        if "Year of birth" in user_info:
            user_info["Year of birth"] = int(user_info["Year of birth"])

        institution_tags = ["work", "education"]
        for institution_tag in institution_tags:
            found_tag = soup.find("div", attrs={"id": institution_tag})
            if found_tag:
                found_img_tag = found_tag.find("img")
                if found_img_tag and "alt" in found_img_tag.attrs:
                    user_info[institution_tag.capitalize()] = \
                        found_img_tag.attrs["alt"]

        relationship_tag = soup.find("div", attrs={"id": "relationship"})
        if relationship_tag:

            relationship_choices = [
                'In a relationship', 'Engaged', 'Married',
                'In a civil partnership', 'In a domestic partnership',
                'In an open relationship', 'It\'s complicated', 'Separated',
                'Divorced', 'Widowed', 'Single'
            ]
            for relationship_choice in relationship_choices:
                if relationship_choice in relationship_tag.text:
                    user_info["Relationship"] = relationship_choice
                    break

        return user_info

    def parse_friends_page(self, content):
        """Extract information from the mobile version of the friends page.

        JavaScript has to be disabled when fetching the page, otherwise, the
        content returned by requests does not contain the UIDs.

        Returns an OrderedDict([('111', {'Name': ''}), ...]) mapping user ids
        to names.

        >>> FacebookSoupParser().parse_friends_page('''
        ...     <div id="friends_center_main">
        ...         <a href="/privacyx/selector/">
        ...         <a class="bn" href="/friends/hovercard/mbasic/?
        ...             uid=111&amp;redirectURI=https%3A%2F%2Fm.facebook.com
        ...         ">Mark</a>
        ...         <a class="bn" href="/friends/hovercard/mbasic/?
        ...             uid=222&amp;redirectURI=https%3A%2F%2Fm.facebook.com
        ...         ">Dave</a>
        ...         <a href="/friends/center/friends/?ppk=1&amp;
        ...             tid=u_0_0&amp;bph=1#friends_center_main">
        ...     </div>''')
        OrderedDict([('111', {'Name': 'Mark'}), ('222', {'Name': 'Dave'})])
        >>> FacebookSoupParser().parse_friends_page('''
        ...     <div id="friends_center_main">
        ...         <a href="/privacyx/selector/">
        ...         <a href="/friends/center/friends/?ppk=1&amp;
        ...             tid=u_0_0&amp;bph=1#friends_center_main">
        ...     </div>''')
        OrderedDict()
        >>> FacebookSoupParser().parse_friends_page('''
        ...     <div id="friends_center_main">
        ...     </div>''')
        OrderedDict()
        >>> FacebookSoupParser().parse_friends_page("")
        OrderedDict()
        """

        soup = BeautifulSoup(content, "lxml")

        friends_found = OrderedDict()

        main_soup = soup.find(id="friends_center_main")
        if not main_soup:
            logging.error("Failed to parse friends page")
            return friends_found

        links_soup = main_soup.find_all("a")
        for link in links_soup:
            if "href" in link.attrs:
                uid_found = re.findall(r'uid=\d+', link.attrs["href"])
                if uid_found:
                    friends_found[uid_found[0].replace("uid=", "")] =\
                        {"Name": link.text}

        return friends_found
