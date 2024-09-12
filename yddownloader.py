import streamlit as st
import cloudscraper
from urllib.parse import urlparse, urlunparse, parse_qs
from datetime import datetime
import zipfile
import os
from io import BytesIO

BASE_URL = "https://api.yodayo.com/v1/users/{user_id}/posts"
LIMIT = 500

scraper = cloudscraper.create_scraper()

@st.cache_data(ttl=3200)
def fetch_posts(user_id, limit, offset):
    url = BASE_URL.format(user_id=user_id)
    params = {"offset": offset, "limit": limit, "width": 2688, "include_nsfw": "true"}
    response = scraper.get(url, params=params)
    response.raise_for_status()
    return response.json()

def filter_posts_by_date(posts, start_date, end_date):
    start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    return [
        post for post in posts
        if start_date <= datetime.fromisoformat(post["created_at"].replace("Z", "+00:00")) <= end_date
    ]

@st.cache_data(ttl=3200)
def clean_url(url):
    original_url = url
    if "_" in url:
        url = url[:url.rfind("_")] + (".png" if ".png" in url else "")
    if not url.endswith((".jpg", ".png")):
        url += ".jpg" if ".jpg" in url else ".png"

    try:
        response = scraper.head(url, timeout=0.2)
        response.raise_for_status()
        return url
    except:
        return original_url

def download_images(urls):
    for url in urls:
        response = scraper.get(url)
        response.raise_for_status()
        filename = url.split("/")[-1]
        if not filename.endswith(".jpg"):
            filename += ".jpg"
        yield filename, response.content

@st.fragment(run_every=None)
def download_zip(urls_to_download):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for filename, content in download_images(urls_to_download):
            zip_file.writestr(filename, content)

    zip_buffer.seek(0)
    st.download_button(
        label="Download ZIP",
        data=zip_buffer,
        file_name="images.zip",
        mime="application/zip",
    )

def main():
    st.title("Yodayo Image Downloader")

    user_id = st.text_input("Enter User ID", "")
    start_date = st.text_input("Enter Start Date (YYYY-MM-DDTHH:MM:SSZ)", "2024-05-27T00:00:00Z")
    end_date = st.text_input("Enter End Date (YYYY-MM-DDTHH:MM:SSZ)", "2024-05-28T00:00:00Z")

    if st.button("Download Images"):
        if user_id and start_date and end_date:
            start_date_obj = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_date_obj = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

            if start_date_obj > end_date_obj:
                st.error("Start date cannot be later than end date.")
            else:
                offset = 0
                urls_to_download = []

                while True:
                    posts = fetch_posts(user_id, LIMIT, offset)
                    if not posts:
                        break
                    
                    filtered_posts = filter_posts_by_date(posts, start_date, end_date)
                    for post in filtered_posts:
                        for media in post.get("photo_media", []):
                            clean_media_url = clean_url(media["url"])
                            urls_to_download.append(clean_media_url)
                    
                    offset += LIMIT

                if not urls_to_download:
                    st.error("No images found for the specified date range.")
                else:
                    download_zip(urls_to_download)
        else:
            st.error("Please provide all required inputs.")

if __name__ == "__main__":
    main()