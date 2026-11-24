# Personal Portfolio

A responsive, warm-editorial personal portfolio built with HTML5, CSS3 and vanilla JavaScript. No build step or framework is required.

## Run locally

1. Extract the ZIP.
2. Open `index.html` in a browser, or run a local static server from this folder:
   - Python: `python -m http.server 8000`
   - Then visit `http://localhost:8000`.

## Personalize the website

Edit **`site-data.js`**. It is the single source of truth for personal information and all dynamic sections.

### Basic details

```js
personal: {
  name: "Your Full Name",
  firstName: "Your First Name",
  title: "A short headline about what you do.",
  subtitle: "STUDENT · DEVELOPER",
  intro: "A short introduction for the homepage.",
  about: ["First paragraph.", "Second paragraph."],
  profileImage: "assets/profile.jpg",
  email: "you@example.com",
  location: "Your City, Country",
  resumeUrl: "assets/resume.pdf"
}
```

Use an empty string for optional fields you do not want to show.

### Replace the profile photograph

Place your photograph at `assets/profile.jpg`, or change `personal.profileImage` to another relative path. The image is cropped with `object-fit: cover`; change `object-position` in `style.css` if you need to adjust the crop. If the file is missing, a typographic placeholder appears.

### Add and remove skills

```js
skills: [
  {
    category: "Frontend",
    items: [
      { name: "HTML", level: "Intermediate", description: "Semantic page structure" },
      { name: "CSS", level: "Learning" }
    ]
  }
]
```

Add another category object for another group. Remove an item or use an empty array to hide the skills content. No percentage bars are used.

### Add projects

```js
projects: [
  {
    name: "Project name",
    description: "What the project does.",
    technologies: ["HTML", "CSS", "JavaScript"],
    githubUrl: "https://github.com/yourname/project",
    liveUrl: "https://example.com",
    image: "assets/projects/project-one.jpg",
    status: "Completed",
    category: "Web development"
  }
]
```

Project images are optional. When no image is supplied, the project title is used in a minimal typographic fallback. Links are only displayed when valid HTTP(S) URLs are provided.

### Add certifications

```js
certifications: [
  {
    name: "Credential name",
    provider: "Issuing organization",
    year: "2026",
    verificationUrl: "https://example.com/verify"
  }
]
```

Certification entries are automatically sorted by year. Verification links are optional.

### Update social links

```js
social: {
  github: "https://github.com/yourname",
  linkedin: "https://linkedin.com/in/yourname",
  instagram: "",
  portfolio: "",
  other: [
    { label: "Behance", url: "https://behance.net/yourname" }
  ]
}
```

Only valid links are displayed. Set unused values to empty strings.

### Interests and languages

```js
languages: ["English", "Gujarati"],
interests: ["Music", "Creative coding", "Motion design"]
```

The corresponding sections appear only when these arrays contain values.

### Update education

Education entries are stored in the `education` array. The starter data includes the supplied qualifications:

- B.Tech in Computer Science and Engineering (CSE) — Currently Pursuing; Expected Graduation: 2029.
- Diploma in Information Technology — LJ Polytechnic, Ahmedabad; Completed in 2026.

Edit these objects or add more entries. No grades or achievements are assumed.

## Change the theme

The default is warm light. Visitors can use the ◐ control in the navigation to switch between light and dark. Their choice is saved in browser `localStorage`. Palette values are CSS custom properties at the top of `style.css`.

## Deploy

This is a static website. Upload the extracted folder as-is; keep `index.html`, `style.css`, `script.js`, `site-data.js` and `assets/` together.

### Netlify
1. Sign in to Netlify and choose **Add new site → Deploy manually**.
2. Drag the extracted portfolio folder into the deploy area.
3. Netlify serves `index.html` automatically.

### Vercel
1. Import the folder through a Git repository, or use Vercel CLI.
2. Choose **Other** as the framework preset.
3. Leave the build command empty and set the output directory to `.`.
4. Deploy.

### GitHub Pages
1. Create a repository and upload the contents of this folder to its root.
2. Open **Settings → Pages**.
3. Select **Deploy from a branch**, choose the `main` branch and `/ (root)`.
4. Save and wait for the published URL.

## Contact form

The contact form uses a `mailto:` link and opens the visitor's email application with a prefilled message. It does not send mail by itself. For a hosted form, connect a form provider and update the submit handler in `script.js`.

## Accessibility and performance

- Semantic landmarks and labelled form fields.
- Keyboard-accessible navigation and controls.
- Reduced-motion preference support.
- No arbitrary skill percentage bars.
- No fabricated projects, certifications, social profiles or links.
- No framework, package manager or build process.
