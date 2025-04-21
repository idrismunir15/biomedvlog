import requests
import random
from datetime import date
from gtts import gTTS
from moviepy.editor import TextClip, ImageClip, AudioFileClip, CompositeVideoClip, ColorClip
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
from dotenv import load_dotenv
import urllib.request

# Load environment variables
load_dotenv()

# Fetch Biomedical Concept
def get_biomedical_concept():
    fallback_topics = [
        "CRISPR", "Immunotherapy", "mRNA Vaccines", "Microbiome", "Stem Cells"
    ]
    try:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        params = {"db": "pubmed", "term": "biomedicine", "retmax": 5, "retmode": "json"}
        response = requests.get(url, params=params).json()
        articles = response["esearchresult"]["idlist"]
        if articles:
            article_id = random.choice(articles)
            summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            summary_params = {"db": "pubmed", "id": article_id, "retmode": "json"}
            summary = requests.get(summary_url, params=summary_params).json()
            return summary["result"][article_id]["title"][:100]  # Truncate long titles
    except Exception as e:
        print(f"PubMed error: {e}")
    return random.choice(fallback_topics)

# Fetch Image from Unsplash
def fetch_unsplash_image(query, output_path="background.jpg"):
    try:
        url = "https://api.unsplash.com/search/photos"
        headers = {"Authorization": f"Client-ID {os.getenv('UNSPLASH_ACCESS_KEY')}"}
        params = {"query": query, "per_page": 1, "orientation": "landscape"}
        response = requests.get(url, headers=headers, params=params).json()
        if response["results"]:
            image_url = response["results"][0]["urls"]["regular"]
            urllib.request.urlretrieve(image_url, output_path)
            return output_path
    except Exception as e:
        print(f"Unsplash error: {e}")
        # Fallback to a default image or gradient
        ColorClip(size=(1280, 720), color=(0, 50, 100)).save_frame(output_path)
        return output_path

# Create Video with Visuals
def create_video(concept, output_path="video.mp4"):
    # Narration
    narration_text = f"Today’s biomedical topic: {concept}. Discover its role in advancing medicine!"
    tts = gTTS(text=narration_text, lang="en")
    audio_path = "narration.mp3"
    tts.save(audio_path)
    audio = AudioFileClip(audio_path)
    duration = audio.duration + 1  # Extend video slightly beyond audio

    # Fetch background image
    background_path = fetch_unsplash_image(concept.replace(" ", "+"))
    background = ImageClip(background_path).set_duration(duration).resize((1280, 720))

    # Add semi-transparent overlay for text readability
    overlay = ColorClip(size=(1280, 720), color=(0, 0, 0, 100)).set_duration(duration).set_opacity(0.4)

    # Title text (fade in/out)
    title_clip = TextClip(
        concept, fontsize=50, color="white", size=(1280, 720), font="Arial",
        stroke_color="black", stroke_width=1
    ).set_duration(duration).set_position(("center", "center")).crossfadein(0.5).crossfadeout(0.5)

    # Intro text
    intro_clip = TextClip(
        "Biomedical Concept of the Day", fontsize=30, color="white", font="Arial",
        stroke_color="black", stroke_width=1
    ).set_duration(2).set_position(("center", 50)).crossfadein(0.5)

    # Combine clips
    video = CompositeVideoClip([background, overlay, title_clip, intro_clip])
    video = video.set_audio(audio)
    video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)

    # Clean up
    os.remove(audio_path)
    if os.path.exists(background_path):
        os.remove(background_path)
    return output_path

# Upload to YouTube
def upload_to_youtube(video_path, title, description):
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
    credentials = flow.run_local_server(port=0)
    youtube = build("youtube", "v3", credentials=credentials)

    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["biomedical", "science", "health"],
            "categoryId": "28"  # Science & Technology
        },
        "status": {"privacyStatus": "public"}
    }

    media = MediaFileUpload(video_path)
    request = youtube.videos().insert(
        part="snippet,status", body=request_body, media_body=media
    )
    response = request.execute()
    print(f"Uploaded: https://youtu.be/{response['id']}")
    return response["id"]

# Main
def main():
    concept = get_biomedical_concept()
    print(f"Concept: {concept}")

    video_path = create_video(concept)

    title = f"Biomedical Concept: {concept} ({date.today()})"
    description = f"Explore {concept} in today’s video! Subscribe for daily biomedical topics."
    upload_to_youtube(video_path, title, description)

    os.remove(video_path)

if __name__ == "__main__":
    main()
