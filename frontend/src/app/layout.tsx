import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Biotech Deal Network',
  description: 'Graph-first, asset-aware biotech deal network explorer',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">
          {/* Navigation */}
          <nav className="bg-white shadow-sm border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between h-16">
                <div className="flex items-center">
                  <a href="/" className="flex items-center space-x-2">
                    <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-green-500 rounded-lg" />
                    <span className="font-semibold text-xl text-gray-900">
                      BD Network
                    </span>
                  </a>
                  <div className="hidden md:flex ml-10 space-x-8">
                    <a
                      href="/"
                      className="text-gray-600 hover:text-gray-900 px-3 py-2 text-sm font-medium"
                    >
                      Network
                    </a>
                    <a
                      href="/landscape"
                      className="text-gray-600 hover:text-gray-900 px-3 py-2 text-sm font-medium"
                    >
                      Landscape
                    </a>
                  </div>
                </div>
                <div className="flex items-center">
                  <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">
                    POC v0.1
                  </span>
                </div>
              </div>
            </div>
          </nav>

          {/* Main content */}
          <main>{children}</main>

          {/* Footer */}
          <footer className="bg-white border-t border-gray-200 mt-auto">
            <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
              <p className="text-xs text-gray-400 text-center">
                Data sourced from ClinicalTrials.gov. For informational purposes only.
                Not medical advice.
              </p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
