# Setup

## Palette

- Canvas: `#0B0F14`
- Surface: `#111827`
- Blue: `#60A5FA`
- Cyan: `#67E8F9`
- Slate: `#94A3B8`
- Snow: `#F8FAFC`

## Install

1. Create a public repository whose name exactly matches your GitHub username. Initialize it without a generated README.
2. Copy this bundle into the repository root, preserving `.github/workflows/`, `.github/profile.env`, `assets/`, and `scripts/`.
3. Change only `GITHUB_USERNAME` in `.github/profile.env`. The supplied bundle is already set to `Jyotiraditya21-bug`.
4. Push the files to the `main` branch.
5. Open **Settings → Actions → General → Workflow permissions**, select **Read and write permissions**, and save. No custom secret is required; both workflows use GitHub's automatic `GITHUB_TOKEN`.
6. Open **Actions** and enable workflows if GitHub displays an enable button.
7. Run **Refresh profile content** once. It renders every username-dependent URL, fetches the latest public repositories/activity, and updates the UTC timestamp.
8. Run **Generate contribution snake** once. After the `output` branch appears, refresh the profile page to see both light and dark snake variants.

Scheduled refreshes run daily. Public statistics widgets can occasionally be rate-limited; the README includes a self-hosting fallback for `github-readme-stats`.
