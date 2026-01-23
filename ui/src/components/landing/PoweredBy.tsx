export function PoweredBy() {
  const partners = [
    { name: 'Chutes', highlight: true },
    { name: 'Bittensor Subnet 64', highlight: false },
    { name: 'OpenAI Compatible', highlight: false },
    { name: 'Sandy Sandboxes', highlight: false },
  ];

  return (
    <section className="py-12 lg:py-16 border-t border-b border-[#1F2937]/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <p className="text-center text-sm text-[#6B7280] uppercase tracking-wider mb-8">
          Powered By
        </p>

        <div className="flex flex-wrap justify-center items-center gap-8 lg:gap-16">
          {partners.map((partner) => (
            <div
              key={partner.name}
              className={`text-lg font-medium ${
                partner.highlight ? 'text-[#63D297]' : 'text-[#6B7280]'
              } hover:text-[#F3F4F6] transition-colors cursor-default`}
            >
              {partner.name}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
