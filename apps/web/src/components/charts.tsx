"use client";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  AreaChart,
  Area,
  Cell,
} from "recharts";
import { money } from "@/lib/api";
const colors = [
  "#245e4f",
  "#477e63",
  "#759e80",
  "#a7b99a",
  "#c4cdae",
  "#d8d8be",
  "#aaa78b",
  "#838f79",
];
export function CategoryChart({
  data,
}: {
  data: { name: string; value: number }[];
}) {
  return (
    <div className="chart" role="img" aria-label="Inventory value by category">
      <ResponsiveContainer width="100%" height={270}>
        <BarChart
          data={data}
          margin={{ top: 10, right: 10, left: 0, bottom: 10 }}
        >
          <CartesianGrid vertical={false} stroke="#eeeee8" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v) => `$${v / 1000}k`}
            tick={{ fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={48}
          />
          <Tooltip
            formatter={(v) => money(Number(v))}
            cursor={{ fill: "#f3f4ed" }}
          />
          <Bar
            dataKey="value"
            name="Inventory value"
            radius={[4, 4, 0, 0]}
            maxBarSize={38}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={colors[i % colors.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
export function SalesChart({
  data,
}: {
  data: { date: string; units: number }[];
}) {
  return (
    <div
      className="chart"
      role="img"
      aria-label="Daily units sold over the last 90 days"
    >
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart
          data={data}
          margin={{ top: 10, right: 10, left: -20, bottom: 10 }}
        >
          <defs>
            <linearGradient id="salesFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#447e64" stopOpacity={0.25} />
              <stop offset="100%" stopColor="#447e64" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} stroke="#eeeee8" />
          <XAxis
            dataKey="date"
            tickFormatter={(v) => String(v).slice(5)}
            minTickGap={40}
            tick={{ fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip />
          <Area
            type="monotone"
            dataKey="units"
            name="Units sold"
            stroke="#2c6a54"
            strokeWidth={2}
            fill="url(#salesFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
