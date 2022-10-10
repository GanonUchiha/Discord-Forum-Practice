
from typing import List
import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import unquote, urlparse
import re

# Global variables
URL_PREFIX = "https://forum.gamer.com.tw/"

class PostMetadata:

    def __init__(self, title: str, floor: str, username: str, userid: str, link: str):
        self.title = title
        self.floor = floor
        self.username = username
        self.userid = userid
        self.link = link
    
    @property
    def info(self):
        return "{title} `#{floor}`\nAuthor: {username}({userid})\nLink: <{link}>".format(
            title = self.title,
            floor = self.floor,
            username = self.username,
            userid = self.userid,
            link = self.link
        )

class BahamutPost:
    URL_PREFIX = "https://forum.gamer.com.tw/"
    SEPARATOR = "\n--------------------------------------\n"

    def __init__(self, post: Tag, original_link: str = ""):
        self.post: Tag = post
        self.original_link: str = original_link
        self.metadata: PostMetadata = None
        self.content: str = ""
        self.hashtags: List[str] = []

        self.extract()
    
    @property
    def title(self):
        try:
            return self.metadata.title
        except:
            return ""
    
    @title.setter
    def title(self, new_title: str):
        self.metadata.title = new_title

    @property
    def floor(self):
        try:
            return self.metadata.floor
        except:
            return "-1"
    
    def export(self, include_header: bool = False, include_hashtags: bool = False) -> str:

        output = []

        if include_header:
            output.append(self.metadata.info)
        output.append(self.content)
        if include_hashtags:
            output.append("Hashtags: {}".format(", ".join(self.hashtags)))
        
        return self.SEPARATOR.join(output)

    def extract(self):
        
        self.extract_post_header()
        self.extract_post_body()
        self.extract_hashtags_from_text()

    def extract_post_header(self):
        '''
        Extracts the header from a post.

        ## Parameters:
        post: `Tag`
            A single post, in HTML format
        original_link: `str`
            The original link of the webpage
        '''

        post_header = self.post.find("div", attrs={"class": "c-post__header"})
        try:
            post_title = self.post.find("h1", attrs={"class": "c-post__header__title"}).text
        except:
            post_title = "No Title"
        post_floor = post_header.find("a", attrs={"class": "tippy-gpbp"}).attrs["data-floor"]
        post_href = post_header.find("a", attrs={"class": "tippy-gpbp"}).attrs["href"]
        post_username = post_header.find("a", attrs={"class": "username"}).text
        post_userid = post_header.find("a", attrs={"class": "userid"}).text
        # print("#{} by {}({})".format(post_floor, post_username, post_userid))
        
        if post_href != "":
            post_link = self.URL_PREFIX + post_href
        else:
            post_link = self.original_link

        post_metadata = {
            "title": post_title,
            "floor": post_floor,
            "username": post_username,
            "userid": post_userid,
            "link": post_link
        }
        self.metadata = PostMetadata(**post_metadata)

    def extract_post_body(self):
        '''
        Extracts the main content from a post, and convert it into a pure text format.
        All images, hyperlinks and embeds are replaced with a URL linking to the original content.

        ## Parameters:
        post: `Tag`
            A single post, in HTML format
        '''
        post_body = self.post.find("div", attrs={"class": "c-article__content"})

        # Replace image Tag with image URL
        for img in post_body.find_all("a", attrs={"class": "photoswipe-image"}):
            img: Tag
            img = img.replace_with(img.attrs["href"])

        # Replace YouTube embeds with origininal video URL
        for yt in post_body.find_all("div", attrs={"class": "video-youtube"}):
            yt: Tag
            yt_id = yt.find("iframe").attrs["data-src"].split("/")[-1].split("?")[0]
            yt_link = "https://www.youtube.com/watch?v={}".format(yt_id)
            yt = yt.replace_with(yt_link)

        # Replace Twitch embeds with origininal channel URL
        for tw in post_body.find_all("div", attrs={"class": "video-twitchvod"}):
            tw: Tag
            tw_id = tw.find("iframe").attrs["data-src"].split("&")[0].split("=")[-1]
            tw_link = f"https://www.twitch.tv/{tw_id}"
            tw = tw.replace_with(tw_link)

        # Replace hyperlink Tag with original URL
        for link in post_body.find_all("a"):
            link: Tag
            real_link = unquote(link.attrs["href"]).split("?url=")[-1]
            link = link.replace_with("{} (<{}>)".format(link.text, real_link))
        # print(post_body)

        # Replace br Tags with newlines
        for br in post_body.find_all("br"):
            br: Tag
            br = br.replace_with("\n")

        # Replace div Tags and add newlines
        for div in post_body.find_all("div"):
            div: Tag
            div = div.replace_with(div.text.strip()+"\n")
        # print(post_body)

        self.content = post_body.text

    def extract_hashtags_from_text(self):
        hashtags = re.findall("(#)(\w+)(\Z|\W)", self.content)
        # print(hashtags)
        self.hashtags = [tag[1] for tag in hashtags]

def get_posts(soup: BeautifulSoup) -> List[Tag]:
    sections: List[Tag] = soup.find_all("section", attrs={"class": "c-section"})
    return [tag for tag in sections if "id" in tag.attrs and tag.attrs["id"].startswith("post")]

def get_webpage(url: str) -> requests.Response:
    headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
               "AppleWebKit/537.36 (KHTML, like Gecko)"
               "Chrome/84.0.4147.105 Safari/537.36"}
    response: requests.Response = requests.get(url, headers=headers)
    return response

def main():
    test_link = input("Enter URL: ")
    print(urlparse(test_link))

    response: requests.Response = get_webpage(test_link)
    
    with open("test.html", "w", encoding="utf8") as fp:
        fp.write(response.text)
    
    soup = BeautifulSoup(response.text, features="lxml")
    posts: List[Tag] = get_posts(soup)
    # print([post.attrs for post in posts])
    post: BahamutPost = BahamutPost(posts[0], test_link)
    post.extract(extract_hashtags=True)
    
    # post_metadata: PostMetadata = extract_post_header(posts[0], test_link)
    # post_body_text: str = extract_post_body(posts[0]).strip()
    # post_hashtags: List[str] = extract_hashtags_from_text(post_body_text)
    
    with open("cleaned.txt", "w", encoding="utf8") as fp:
        fp.write(post.export(include_header=True, include_hashtags=True))
        # fp.write(post_metadata.info)
        # fp.write("\n-----------------------------------------\n")
        # fp.write(post_body_text)
        # fp.write("\n-----------------------------------------\n")
        # fp.write("Hashtags: {}".format(", ".join(post_hashtags)))

if __name__ == "__main__":
    main()