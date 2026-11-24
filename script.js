(() => {
  "use strict";
  const data = window.portfolioData || {};
  const personal = data.personal || {};
  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];
  const clean = value => typeof value === "string" ? value.trim() : "";
  const setText = (selector, value) => { const el = $(selector); if (el && clean(value)) el.textContent = value; };

  // Identity and hero
  $$("[data-name]").forEach(el => el.textContent = clean(personal.name) || "YOUR NAME");
  $$("[data-firstname]").forEach(el => el.textContent = clean(personal.firstName) || clean(personal.name) || "YOUR NAME");
  setText("#hero-kicker", personal.subtitle);
  setText("#hero-title", personal.title);
  setText("#hero-intro", personal.intro);
  setText("#hero-location", personal.location ? `BASED IN ${personal.location.toUpperCase()}` : "");
  setText("#portrait-name", personal.name);
  setText("#contact-message", personal.contactMessage);
  setText("#career-goal", personal.careerGoal);
  document.title = `${personal.name || "Portfolio"} — Personal Portfolio`;
  const profile = $("#profile-image");
  if (clean(personal.profileImage)) profile.src = personal.profileImage;
  if (clean(personal.imageAlt)) profile.alt = personal.imageAlt;
  if (clean(personal.resumeUrl)) { $("#resume-link").href = personal.resumeUrl; $("#resume-link").hidden = false; }

  // About paragraphs
  const about = $("#about-copy");
  (Array.isArray(personal.about) ? personal.about : [personal.about]).filter(clean).forEach(text => {
    const p = document.createElement("p"); p.textContent = text; about.append(p);
  });
  if (!about.children.length) about.closest(".about-section").hidden = true;

  // Skills
  const skillsGrid = $("#skills-grid");
  (data.skills || []).filter(group => group && clean(group.category) && Array.isArray(group.items) && group.items.length)
    .forEach(group => {
      const card = document.createElement("article"); card.className = "skill-group";
      const heading = document.createElement("h3"); heading.textContent = group.category; card.append(heading);
      const items = document.createElement("div"); items.className = "skill-items";
      group.items.filter(item => item && clean(item.name)).forEach(item => {
        const tag = document.createElement("span"); tag.className = "skill-item";
        tag.append(document.createTextNode(item.name));
        if (clean(item.level)) { const level = document.createElement("small"); level.className = "skill-level"; level.textContent = item.level; tag.append(level); }
        if (clean(item.description)) tag.title = item.description;
        items.append(tag);
      });
      card.append(items); skillsGrid.append(card);
    });
  if (!skillsGrid.children.length && !(data.interests || []).length && !(data.languages || []).length) $("#skills").hidden = true;

  // Optional interests and languages
  const addTags = (values, wrapSelector, listSelector) => {
    const valuesClean = (values || []).filter(v => clean(v));
    if (!valuesClean.length) return;
    $(wrapSelector).hidden = false;
    valuesClean.forEach(value => { const tag = document.createElement("span"); tag.className = "tag"; tag.textContent = value; $(listSelector).append(tag); });
  };
  addTags(data.interests, "#interests-wrap", "#interests-list");
  addTags(data.languages, "#languages-wrap", "#languages-list");

  // Project cards: only user-supplied links are rendered.
  const projectGrid = $("#projects-grid");
  const projects = (data.projects || []).filter(p => p && clean(p.name));
  $("#projects-empty").hidden = projects.length > 0;
  projects.forEach((project, index) => {
    const card = document.createElement("article"); card.className = "project-card reveal";
    const media = document.createElement("div"); media.className = "project-image";
    if (clean(project.image)) {
      const img = document.createElement("img"); img.src = project.image; img.alt = `${project.name} project preview`;
      img.onerror = () => { img.remove(); media.innerHTML = `<div class="project-placeholder">${escapeHtml(project.name)}</div>`; };
      media.append(img);
    } else {
      const fallback = document.createElement("div"); fallback.className = "project-placeholder"; fallback.textContent = project.name; media.append(fallback);
    }
    const content = document.createElement("div"); content.className = "project-content";
    const top = document.createElement("div"); top.className = "project-topline";
    const category = document.createElement("span"); category.textContent = clean(project.category) || `PROJECT / ${String(index + 1).padStart(2, "0")}`;
    const status = document.createElement("span"); status.textContent = clean(project.status); top.append(category, status);
    const title = document.createElement("h3"); title.textContent = project.name;
    const desc = document.createElement("p"); desc.textContent = clean(project.description);
    content.append(top, title, desc);
    if (Array.isArray(project.technologies) && project.technologies.length) {
      const tech = document.createElement("div"); tech.className = "project-tech";
      project.technologies.filter(clean).forEach(t => { const s = document.createElement("span"); s.textContent = `· ${t}`; tech.append(s); });
      content.append(tech);
    }
    const links = document.createElement("div"); links.className = "project-links";
    [["githubUrl", "GitHub ↗"], ["liveUrl", "Live demo ↗"]].forEach(([key, label]) => {
      if (isSafeUrl(project[key])) { const a = document.createElement("a"); a.href = project[key]; a.target = "_blank"; a.rel = "noopener noreferrer"; a.textContent = label; links.append(a); }
    });
    if (links.children.length) content.append(links);
    card.append(media, content); projectGrid.append(card);
  });

  // Certifications grouped naturally by year.
  const certs = data.certifications || [];
  if (certs.length) {
    $("#certifications").hidden = false;
    const list = $("#certifications-list");
    [...certs].filter(c => c && clean(c.name)).sort((a,b) => String(b.year || "").localeCompare(String(a.year || ""))).forEach(cert => {
      const row = document.createElement("article"); row.className = "timeline-item";
      const date = document.createElement("div"); date.className = "timeline-date"; date.textContent = cert.year || "CERTIFICATION";
      const body = document.createElement("div"); const h = document.createElement("h3"); h.textContent = cert.name; body.append(h);
      const provider = document.createElement("p"); provider.textContent = clean(cert.provider); body.append(provider);
      if (isSafeUrl(cert.verificationUrl)) { const a = document.createElement("a"); a.href = cert.verificationUrl; a.target = "_blank"; a.rel = "noopener"; a.className = "timeline-status"; a.textContent = "VERIFY CREDENTIAL ↗"; body.append(a); }
      row.append(date, body); list.append(row);
    });
  }

  // Education timeline
  const education = $("#education-list");
  (data.education || []).filter(e => e && clean(e.qualification)).forEach(item => {
    const row = document.createElement("article"); row.className = "timeline-item reveal";
    const date = document.createElement("div"); date.className = "timeline-date"; date.textContent = [item.start, item.end].filter(clean).join(" — ") || "EDUCATION";
    const body = document.createElement("div"); const h = document.createElement("h3"); h.textContent = item.qualification; body.append(h);
    if (clean(item.institution)) { const inst = document.createElement("p"); inst.textContent = item.institution; body.append(inst); }
    if (clean(item.detail)) { const detail = document.createElement("p"); detail.textContent = item.detail; body.append(detail); }
    if (clean(item.status)) { const status = document.createElement("span"); status.className = "timeline-status"; status.textContent = item.status; body.append(status); }
    row.append(date, body); education.append(row);
  });

  // Contact and social profiles
  const emailLink = $("#email-link");
  if (isValidEmail(personal.email)) { emailLink.href = `mailto:${personal.email}`; emailLink.textContent = personal.email; emailLink.hidden = false; }
  const socials = $("#contact-links");
  const socialData = data.social || {};
  const socialEntries = [
    ["github", "GitHub"], ["linkedin", "LinkedIn"], ["instagram", "Instagram"], ["portfolio", "Website"],
    ...((socialData.other || []).filter(item => item && clean(item.label)).map(item => [item.url, item.label]))
  ];
  socialEntries.forEach(([url, label]) => {
    const value = url === "github" || url === "linkedin" || url === "instagram" || url === "portfolio" ? socialData[url] : url;
    if (isSafeUrl(value)) { const a = document.createElement("a"); a.href = value; a.target = "_blank"; a.rel = "noopener noreferrer"; a.textContent = `${label} ↗`; socials.append(a); }
  });
  if (isValidEmail(personal.email)) socials.append(Object.assign(document.createElement("a"), { href: `mailto:${personal.email}`, textContent: "Email ↗" }));
  if (clean(personal.phone)) socials.append(Object.assign(document.createElement("a"), { href: `tel:${personal.phone.replace(/[^\d+]/g, "")}`, textContent: "Phone ↗" }));
  if (!socials.children.length) socials.hidden = true;

  // Contact form prepares a real mailto; no false sent state.
  $("#contact-form").addEventListener("submit", event => {
    event.preventDefault();
    if (!isValidEmail(personal.email)) { $("#form-error").textContent = "Add a valid email address in site-data.js to enable this form."; return; }
    const form = new FormData(event.currentTarget);
    const subject = encodeURIComponent(`Portfolio enquiry from ${form.get("name")}`);
    const body = encodeURIComponent(`Name: ${form.get("name")}\nEmail: ${form.get("email")}\n\n${form.get("message")}`);
    window.location.href = `mailto:${personal.email}?subject=${subject}&body=${body}`;
  });

  // Theme persistence
  const themeButton = $(".theme-toggle");
  const savedTheme = localStorage.getItem("portfolio-theme");
  if (savedTheme === "dark" || savedTheme === "light") document.documentElement.dataset.theme = savedTheme;
  const updateThemeButton = () => {
    const dark = document.documentElement.dataset.theme === "dark";
    themeButton.textContent = dark ? "☼" : "◐";
    themeButton.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  };
  updateThemeButton();
  themeButton.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next; localStorage.setItem("portfolio-theme", next); updateThemeButton();
  });

  // Mobile navigation
  const menuButton = $(".menu-toggle"), nav = $(".main-nav");
  menuButton.addEventListener("click", () => {
    const open = nav.classList.toggle("open"); menuButton.setAttribute("aria-expanded", String(open));
    menuButton.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
  });
  $$(".nav-link", nav).forEach(link => link.addEventListener("click", () => { nav.classList.remove("open"); menuButton.setAttribute("aria-expanded", "false"); }));

  // Active section, reveal and reading progress
  const sections = $$("main section[id]").filter(s => !s.hidden);
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) {
        $$(".nav-link").forEach(link => link.classList.toggle("active", link.getAttribute("href") === `#${entry.target.id}`));
        entry.target.classList.add("visible");
      }
    }), { rootMargin: "-35% 0px -55% 0px" });
    sections.forEach(section => observer.observe(section));
    const revealObserver = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add("visible"); revealObserver.unobserve(entry.target); }
    }), { threshold: .08 });
    $$(".project-card, .timeline-item").forEach(el => { el.classList.add("reveal"); revealObserver.observe(el); });
  }
  window.addEventListener("scroll", () => {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    $(".scroll-progress").style.width = `${max > 0 ? window.scrollY / max * 100 : 0}%`;
  }, { passive: true });
  $("#year").textContent = new Date().getFullYear();

  function isValidEmail(value) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(clean(value)); }
  function isSafeUrl(value) { try { const url = new URL(value); return ["http:", "https:"].includes(url.protocol); } catch { return false; } }
  function escapeHtml(value) { return String(value).replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c])); }
})();
