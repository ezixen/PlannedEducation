export function Dashboard() {
  return (
    <div>
      <h1>Welcome to PlannedEducation</h1>
      <p>Select an option from the menu to get started.</p>
      
      <div style={{ marginTop: '2rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
        <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <h3>Recent Exams</h3>
          <p>No recent exams found.</p>
        </div>
        
        <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <h3>Upcoming Assignments</h3>
          <p>You are all caught up!</p>
        </div>
      </div>
    </div>
  );
}
