type PipelineProps = { compact?: boolean };

export function SpeculativePipeline({ compact = false }: PipelineProps) {
  return (
    <svg aria-label="投机解码流程示意图" className={compact ? 'h-36 w-full' : 'h-44 w-full'} viewBox="0 0 720 190">
      <defs>
        <marker id="pipeline-arrow" markerHeight="8" markerWidth="8" orient="auto" refX="6" refY="3">
          <path d="M0 0 6 3 0 6" fill="none" stroke="#30343b" strokeWidth="1.4" />
        </marker>
      </defs>
      {[
        { x: 12, w: 116, title: 'Prompt', sub: '输入提示', stroke: '#aab1bf' },
        { x: 165, w: 160, title: 'Draft Model', sub: '生成候选 tokens', stroke: '#315cff' },
        { x: 363, w: 166, title: 'Target Verify', sub: '并行验证', stroke: '#745cfa' },
        { x: 566, w: 142, title: 'Accept / Reject', sub: '接受或重采样', stroke: '#aab1bf' },
      ].map((node) => (
        <g key={node.title}>
          <rect fill="#fff" height="104" rx="8" stroke={node.stroke} strokeWidth="1.5" width={node.w} x={node.x} y="25" />
          <text fill="#15171c" fontSize="14" fontWeight="700" textAnchor="middle" x={node.x + node.w / 2} y="52">{node.title}</text>
          <text fill="#666b76" fontSize="11" textAnchor="middle" x={node.x + node.w / 2} y="71">{node.sub}</text>
          {node.x > 130 && [0, 1, 2, 3, 4].map((token) => (
            <rect fill={node.x === 363 ? (token === 4 ? '#fff0f0' : '#ecfff2') : '#eef2ff'} height="17" key={token} rx="2" stroke={token === 4 && node.x === 363 ? '#ef4444' : node.stroke} width="17" x={node.x + 18 + token * 23} y="91" />
          ))}
        </g>
      ))}
      {[128, 325, 529].map((x) => <path d={`M${x + 7} 77h25`} key={x} markerEnd="url(#pipeline-arrow)" stroke="#30343b" />)}
      <g transform="translate(174 153)">
        <rect fill="#ebfff2" height="21" rx="4" stroke="#24a05a" width="21" />
        <path d="m5 10 4 4 7-8" fill="none" stroke="#168847" strokeWidth="2" />
        <text fill="#4b505b" fontSize="11" x="28" y="15">接受 Accepted</text>
        <rect fill="#fff1f1" height="21" rx="4" stroke="#ef4444" width="21" x="132" />
        <path d="m138 6 9 9m0-9-9 9" stroke="#dc2626" strokeWidth="1.8" />
        <text fill="#4b505b" fontSize="11" x="160" y="15">拒绝 Rejected</text>
      </g>
    </svg>
  );
}

export function KvCacheMatrix() {
  const cells = Array.from({ length: 48 });
  return (
    <svg aria-label="KV Cache 占用矩阵示意图" className="h-40 w-full" viewBox="0 0 440 180">
      <text fill="#343841" fontSize="12" fontWeight="600" x="18" y="22">KV Cache 布局（层 × 头 × Token）</text>
      {cells.map((_, index) => {
        const row = Math.floor(index / 12);
        const col = index % 12;
        const occupied = col < 7 - row || (row === 2 && col < 10);
        return <rect fill={occupied ? (index % 3 ? '#75a1ff' : '#315cff') : '#f1f2f4'} height="20" key={index} rx="2" stroke={occupied ? '#315cff' : '#cfd2d8'} width="23" x={80 + col * 27} y={35 + row * 25} />;
      })}
      {[0, 1, 2, 3].map((row) => <text fill="#626672" fontSize="10" key={row} textAnchor="end" x="70" y={49 + row * 25}>Layer {row}</text>)}
      <path d="M80 151h312" stroke="#d5d7dd" />
      <text fill="#737782" fontSize="10" x="80" y="168">Token 1</text>
      <text fill="#737782" fontSize="10" textAnchor="end" x="392" y="168">Token T</text>
    </svg>
  );
}

export function ServingTopology() {
  const nodes = [
    { x: 115, y: 40, label: '调度策略', color: '#745cfa' },
    { x: 66, y: 94, label: '并发处理', color: '#24a05a' },
    { x: 158, y: 148, label: '模型与推理', color: '#315cff' },
    { x: 250, y: 94, label: '系统资源', color: '#ed8612' },
  ];
  return (
    <svg aria-label="LLM Serving 优化知识图" className="h-48 w-full" viewBox="0 0 330 195">
      <circle cx="165" cy="96" fill="#315cff" r="39" />
      <text fill="white" fontSize="12" fontWeight="700" textAnchor="middle" x="165" y="92">LLM Serving</text>
      <text fill="white" fontSize="11" textAnchor="middle" x="165" y="108">Optimization</text>
      {nodes.map((node) => (
        <g key={node.label}>
          <path d={`M165 96L${node.x + 35} ${node.y + 12}`} opacity=".7" stroke={node.color} />
          <rect fill="white" height="25" rx="5" stroke={node.color} width="72" x={node.x} y={node.y} />
          <text fill={node.color} fontSize="10" fontWeight="600" textAnchor="middle" x={node.x + 36} y={node.y + 16}>{node.label}</text>
        </g>
      ))}
    </svg>
  );
}

export function PerformanceChart({ dark = false }: { dark?: boolean }) {
  const stroke = dark ? '#6b7280' : '#d7d9df';
  const text = dark ? '#a9b0bb' : '#707580';
  return (
    <svg aria-label="吞吐与延迟示意曲线" className="h-44 w-full" viewBox="0 0 430 205">
      <g stroke={stroke} strokeWidth="1">
        <path d="M45 15v155h365" />
        <path d="M45 50h365M45 90h365M45 130h365" opacity=".45" />
      </g>
      <path d="M62 40C118 50 154 62 198 79s91 43 190 70" fill="none" stroke="#9298a2" strokeWidth="2.3" />
      <path d="M62 68C114 88 158 102 202 116s101 31 186 42" fill="none" stroke="#315cff" strokeWidth="2.6" />
      {[62, 111, 156, 202, 258, 321, 388].map((x, i) => <circle cx={x} cy={[68, 87, 102, 116, 132, 147, 158][i]} fill={dark ? '#151a1d' : '#fff'} key={x} r="3.4" stroke="#315cff" strokeWidth="2" />)}
      <text fill={text} fontSize="10" textAnchor="middle" x="224" y="195">吞吐量（tokens/s）</text>
      <text fill={text} fontSize="10" transform="rotate(-90 14 98)" x="14" y="98">延迟（ms/token）</text>
      <g fontSize="10" transform="translate(259 17)">
        <path d="M0 7h20" stroke="#315cff" strokeWidth="2" /><text fill={text} x="25" y="10">Optimized（示意）</text>
        <path d="M0 26h20" stroke="#9298a2" strokeWidth="2" /><text fill={text} x="25" y="29">Baseline（示意）</text>
      </g>
    </svg>
  );
}
