# Screenshots in a walkthrough

Real screenshots show the reviewer the UI faster than any description, so they come right after the summary.

## Find them

- **On the PR.**
  - Read the body and conversation comments with `gh pr view <n> --json body,comments`.
  - Read review comments with `gh api repos/<owner>/<repo>/pulls/<n>/comments` and `gh api repos/<owner>/<repo>/pulls/<n>/reviews`.
  - Take image URLs from Markdown `![alt](url)` and HTML `<img src>`.
- **In this conversation.** Look at images the user attached, and screenshots that earlier work in the thread saved to disk, such as E2E runs. Use the screenshots you took of your own walkthrough page only for verification, never as content.

For each image, keep:
- its caption: the alt text, or the sentence around it;
- its context: which comment it came from, and when.

## Fetch them

Save the images into a new, empty directory, with the extension that matches their real type.

- Download GitHub attachments with:

  ```sh
  curl -sL -H "Authorization: Bearer $(gh auth token)" -o <name> "https://github.com/user-attachments/assets/<id>"
  ```

  On private repositories these return 404 without the token. Curl drops the header when it follows the redirect to the storage host, so the token stays with GitHub.
- Check the type with `file -b --mime-type <name>`, then rename the file to `.png`, `.jpg` and so on. Image viewers and the Read tool treat an unknown extension as binary text.
- Look at every image before using it.

## Place them

Put them in a **What it looks like** section after the summary: a grid of thumbnails, each opening a lightbox. Each caption says what the shot shows and where it came from, such as "From the E2E comment on the PR".

**Date every shot against the commits.** When a shot was taken before a later commit changed that UI, its caption says so, for example "Before the redesign in `09b5a72`". Compare the comment's time and wording with the commit list. The reviewer must never mistake an old screen for the current one.

Reuse a shot inline beside the deep dive it illustrates. Typical pairings:

- the real dialog beside its simulator;
- a permission-limited view beside the access matrix;
- a changed tab beside the section about it.

Prefer a real screenshot over a hand-made mock-up of the same screen.

## Embed them

- Convert each shot to WebP: `magick <in> -quality 80 <out>.webp`. A 1440×1000 capture usually comes out at 40–100 KB.
- Embed the images as base64 data URIs in one JavaScript map keyed by name, and point `<img data-shot="name">` at it. A shot used twice is stored once, and the page stays self-contained.
- Full-screen captures make small thumbnails. Zoom each thumbnail onto the part that matters with a per-figure `transform: scale(var(--zoom))` and `transform-origin: var(--pos)` inside an `overflow: hidden` frame. The lightbox shows the whole image.

## Verify them

In the headless browser, check that every `img[data-shot]` loaded (`naturalWidth > 0`), that the lightbox opens and closes, and that every thumbnail's crop shows its subject.
