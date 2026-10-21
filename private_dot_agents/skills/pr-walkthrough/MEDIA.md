# Screenshots and videos in a walkthrough

Real screenshots and recordings show the reviewer the UI faster than any description, so they come right after the summary, shown large.

## Find them

- **On the PR.**
  - Read the body and conversation comments with `gh pr view <n> --json body,comments`.
  - Read review comments with `gh api repos/<owner>/<repo>/pulls/<n>/comments` and `gh api repos/<owner>/<repo>/pulls/<n>/reviews`.
  - Take image URLs from Markdown `![alt](url)` and HTML `<img src>`, and video URLs from `<video src>` and from bare `https://github.com/user-attachments/assets/<id>` links on a line of their own, which is how GitHub embeds uploaded videos.
- **In this conversation.** Look at images the user attached, and screenshots or recordings that earlier work in the thread saved to disk, such as E2E runs. Use the screenshots you took of your own walkthrough page only for verification, never as content.

For each item, keep:
- its caption: the alt text, or the sentence around it;
- its context: which comment it came from, and when.

## Fetch them

Save everything into a new, empty directory, with the extension that matches its real type.

- Download GitHub attachments with:

  ```sh
  curl -sL -H "Authorization: Bearer $(gh auth token)" -o <name> "https://github.com/user-attachments/assets/<id>"
  ```

  On private repositories these return 404 without the token. Curl drops the header when it follows the redirect to the storage host, so the token stays with GitHub.
- Check the type with `file -b --mime-type <name>`, then rename the file to `.png`, `.jpg`, `.mp4` and so on. Image viewers and the Read tool treat an unknown extension as binary text.
- Look at every image. For a video, look at a few frames: `ffmpeg -i <in> -vf fps=1/3 -frames:v 4 frame-%d.png`.

## Place them

Put them in **What it looks like**, after the summary.

- Show each shot at the full content width, one per row, uncropped, so its text is readable without opening it. Put two side by side (`.media.pair`) only for a before/after or a pair of states meant to be compared.
- Show a video inline with `controls muted loop playsinline`, at full width.
- A click on a shot opens the lightbox at full size.
- Each caption says what the shot shows and where it came from, such as "From the E2E comment on the PR".

**Date every shot against the commits.** When a shot was taken before a later commit changed that UI, its caption says so, for example "Before the redesign in `09b5a72`". Compare the comment's time with the commits, and check which files each later commit touches: after a rebase, commit dates postdate the shots, so the touched files are what tell you whether the screen changed. The reviewer must never mistake an old screen for the current one.

A deep dive that a shot illustrates links to it in its caption rather than repeating it. Prefer a real screenshot over a hand-made mock-up of the same screen.

## Embed them

- Convert each shot to WebP: `magick <in> -quality 82 <out>.webp`.
- Compress each video to H.264 MP4 without audio:

  ```sh
  ffmpeg -i <in> -vf "scale='min(1600,iw)':-2" -c:v libx264 -crf 28 -preset veryfast -an -movflags +faststart <out>.mp4
  ```

- Embed images and videos as base64 data URIs in the template's `SHOTS` map, keyed by name, and point `<img data-shot="name">` at it, so a shot used twice is stored once. Set a video's `src` from the same map.
- When a video is still over 15 MB, save it next to the page as `pr-<n>-<name>.mp4` and reference it by relative path, and say so in the reply.

## Verify them

In the headless browser, check that every `img[data-shot]` loaded (`naturalWidth > 0`), that every `video` has `readyState > 0`, and that the lightbox opens and closes.
