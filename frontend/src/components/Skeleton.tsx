interface SkeletonProps {
  className?: string;
  style?: React.CSSProperties;
}

export function Bone({ className = "", style }: SkeletonProps) {
  return <div className={`sk sk-bone ${className}`} style={style} />;
}

export function BoneLine({ width = "100%", height = 16 }: { width?: string | number; height?: number }) {
  return <div className="sk sk-bone sk-line" style={{ width, height }} />;
}

export function BoneCircle({ size = 40 }: { size?: number }) {
  return <div className="sk sk-bone sk-circle" style={{ width: size, height: size }} />;
}

export function StatCardSkeleton() {
  return (
    <div className="sk-card">
      <BoneCircle size={36} />
      <div className="sk-card-lines">
        <BoneLine width="50%" height={24} />
        <BoneLine width="70%" height={12} />
      </div>
    </div>
  );
}

export function JobCardSkeleton() {
  return (
    <div className="sk-card sk-job-card">
      <div className="sk-job-left">
        <Bone style={{ width: 42, height: 28, borderRadius: 8 }} />
        <div className="sk-job-lines">
          <BoneLine width="60%" />
          <BoneLine width="40%" />
        </div>
      </div>
      <div className="sk-tags">
        <Bone style={{ width: 56, height: 22, borderRadius: 11 }} />
        <Bone style={{ width: 48, height: 22, borderRadius: 11 }} />
      </div>
    </div>
  );
}

export function ListItemSkeleton({ hasAvatar = true }: { hasAvatar?: boolean }) {
  return (
    <div className="sk-card sk-list-item">
      {hasAvatar && <BoneCircle size={36} />}
      <div className="sk-item-body">
        <BoneLine width="55%" />
        <BoneLine width="35%" height={12} />
        <div className="sk-tags">
          <Bone style={{ width: 52, height: 20, borderRadius: 10 }} />
          <Bone style={{ width: 44, height: 20, borderRadius: 10 }} />
        </div>
      </div>
    </div>
  );
}

export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="sk-table">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="sk-table-row">
          {Array.from({ length: cols }).map((_, j) => (
            <Bone key={j} style={{ height: 16, width: `${60 + (j % 3) * 15}%` }} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function PageSkeleton({ cards = 4 }: { cards?: number }) {
  return (
    <>
      <div className="page-header"><div><div className="sk sk-bone" style={{ width: 180, height: 28 }} /></div></div>
      <div className="sk-grid">
        {Array.from({ length: cards }).map((_, i) => (
          <JobCardSkeleton key={i} />
        ))}
      </div>
    </>
  );
}
