const PAGE_TITLE = 'SafeCity AI — Real-Time Public Safety Intelligence';

export function SublevelStudioLandingPage() {
  return (
    <main className="sublevel-studio-viewport">
      <iframe
        title={PAGE_TITLE}
        src="https://threeui.com/landing-pages/sublevel-studio.html"
        loading="eager"
        sandbox="allow-downloads allow-forms allow-modals allow-popups allow-same-origin allow-scripts"
      />
    </main>
  );
}
