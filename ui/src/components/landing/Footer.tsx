import Link from 'next/link';

export function Footer() {
  const footerLinks = {
    Product: [
      { label: 'Chat', href: '/chat' },
      { label: 'Competition', href: '/competition' },
      { label: 'Marketplace', href: '/marketplace' },
    ],
    Resources: [
      { label: 'Documentation', href: '/docs' },
      { label: 'API Reference', href: '/docs' },
      { label: 'GitHub', href: 'https://github.com/chutesai' },
    ],
    Company: [
      { label: 'About', href: '#' },
      { label: 'Blog', href: '#' },
      { label: 'Contact', href: '#' },
    ],
  };

  return (
    <footer className="py-12 lg:py-16 border-t border-[#1F2937]/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid md:grid-cols-4 gap-8 lg:gap-12 mb-12">
          {/* Brand */}
          <div>
            <Link href="/" className="text-2xl font-semibold text-[#F3F4F6] mb-4 block">
              JANUS
            </Link>
            <p className="text-[#9CA3AF] text-sm leading-relaxed mb-4">
              The Open Intelligence Rodeo. Build the intelligence engine on Bittensor.
            </p>
            <div className="flex items-center gap-2 text-sm text-[#6B7280]">
              <span>Powered by</span>
              <span className="text-[#63D297] font-medium">Chutes</span>
            </div>
          </div>

          {/* Links */}
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <h4 className="text-sm font-semibold text-[#F3F4F6] uppercase tracking-wider mb-4">
                {category}
              </h4>
              <ul className="space-y-3">
                {links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-[#9CA3AF] hover:text-[#F3F4F6] text-sm transition-colors"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom */}
        <div className="pt-8 border-t border-[#1F2937]/50 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-[#6B7280] text-sm">
            &copy; 2026 Chutes.ai. All rights reserved.
          </p>
          <div className="flex items-center gap-6">
            {/* Twitter/X */}
            <a
              href="https://x.com/chutes_ai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#6B7280] hover:text-[#F3F4F6] transition-colors"
              aria-label="X"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
            </a>
            {/* GitHub */}
            <a
              href="https://github.com/chutesai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#6B7280] hover:text-[#F3F4F6] transition-colors"
              aria-label="GitHub"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0012 2z" />
              </svg>
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
