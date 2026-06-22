export default function Loading() {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      minHeight: "100vh",
      background: "var(--bg)",
    }}>
      <div style={{
        width: 36,
        height: 36,
        border: "3px solid var(--border)",
        borderTopColor: "var(--navy)",
        borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
      }} />
    </div>
  );
}
