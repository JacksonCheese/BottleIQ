import Link from "next/link";
import {
  ArrowUpRight,
  Check,
  PackageCheck,
  ShieldCheck,
  CircleDollarSign,
  BarChart3,
} from "lucide-react";
import { Logo } from "@/components/ui";
import { DemoButton } from "@/components/demo-button";
export default function Home() {
  return (
    <div className="landing">
      <header>
        <Logo />
        <nav>
          <a href="#how-it-works">How it works</a>
          <Link href="/login">
            Sign in <ArrowUpRight size={16} />
          </Link>
        </nav>
      </header>
      <main>
        <section className="hero">
          <div className="eyebrow">
            <span className="live-dot" /> INTELLIGENCE FOR INDEPENDENT LIQUOR
            STORES
          </div>
          <h1>
            Stop guessing
            <br />
            what to <em>order.</em>
          </h1>
          <p>
            BottleIQ analyzes your liquor-store sales and inventory and tells
            you what to reorder, what to stop buying, and where your cash is
            tied up.
          </p>
          <div className="hero-actions">
            <DemoButton />
            <Link className="button secondary" href="/signup">
              Create your workspace
            </Link>
          </div>
          <div className="hero-proof">
            <span>
              <Check size={15} />
              Your CSV exports
            </span>
            <span>
              <Check size={15} />
              Clear recommendations
            </span>
            <span>
              <Check size={15} />
              You stay in control
            </span>
          </div>
        </section>
        <section className="landing-example">
          <div>
            <div className="eyebrow">FROM SHELF TO SMART ORDER</div>
            <h2>
              A weekly purchase list
              <br />
              you can explain.
            </h2>
            <p>
              Every recommendation shows the demand, lead time, and safety stock
              behind it.
            </p>
            <span className="badge healthy">ILLUSTRATIVE EXAMPLE</span>
          </div>
          <div className="example-card">
            <div className="example-top">
              <PackageCheck size={22} />
              <span>YOUR NEXT SMART ORDER</span>
              <span className="badge stockout">Reorder soon</span>
            </div>
            <h3>Cedar Ridge Reserve Whiskey</h3>
            <div className="example-numbers">
              <div>
                <small>On your shelf</small>
                <strong>
                  8 <span>bottles</span>
                </strong>
              </div>
              <div>
                <small>Daily demand</small>
                <strong>
                  4 <span>bottles</span>
                </strong>
              </div>
              <div>
                <small>Recommended</small>
                <strong>
                  8 <span>cases</span>
                </strong>
              </div>
            </div>
            <p>
              2 days of stock. A 4-day lead time and 21-day target call for 92
              bottles, rounded to 8 cases of 12.
            </p>
          </div>
        </section>
        <section className="feature-grid">
          {[
            [
              PackageCheck,
              "Smart Orders",
              "Build a purchasing plan for each distributor, adjust quantities, and export a ready-to-review CSV.",
            ],
            [
              ShieldCheck,
              "Stockout Prevention",
              "See what is running low before a best seller leaves an empty spot on your shelf.",
            ],
            [
              CircleDollarSign,
              "Dead Inventory Detection",
              "Find the bottles that stopped moving and the cash you could put to better use.",
            ],
            [
              BarChart3,
              "Profitability Intelligence",
              "Understand gross profit, margin, and inventory returns product by product.",
            ],
          ].map(([Icon, title, copy]) => {
            const I = Icon as typeof PackageCheck;
            return (
              <article key={String(title)}>
                <I size={23} />
                <h3>{String(title)}</h3>
                <p>{String(copy)}</p>
              </article>
            );
          })}
        </section>
        <section id="how-it-works" className="how">
          <div className="eyebrow">THREE STEPS. A CLEARER WEEK.</div>
          <h2>
            Your data is already there.
            <br />
            Put it to work.
          </h2>
          <div>
            {[
              [
                "01",
                "Bring your exports",
                "Upload inventory, sales history, and invoices from your existing systems.",
              ],
              [
                "02",
                "See what matters",
                "Spot stockout risks, slow movers, and the products earning their shelf space.",
              ],
              [
                "03",
                "Order with confidence",
                "Review recommendations by distributor, make adjustments, and export your order.",
              ],
            ].map(([n, t, c]) => (
              <article key={n}>
                <span>{n}</span>
                <h3>{t}</h3>
                <p>{c}</p>
              </article>
            ))}
          </div>
        </section>
      </main>
      <footer>
        <Logo />
        <span>Built for the business behind the bottles.</span>
        <Link href="/signup">
          Get started <ArrowUpRight size={16} />
        </Link>
      </footer>
    </div>
  );
}
