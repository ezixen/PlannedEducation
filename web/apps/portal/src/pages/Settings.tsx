export function Settings() {
  return (
    <div>
      <h1>Settings</h1>
      <p>Configure your application preferences.</p>
      
      <div style={{ marginTop: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <h3>Appearance</h3>
          <p>Theme configuration is available in the top right header.</p>
        </div>

        <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <h3>Account</h3>
          <p>Manage your profile and credentials.</p>
          <button style={{ 
            marginTop: '1rem', 
            padding: '0.5rem 1rem', 
            backgroundColor: 'var(--primary-color)', 
            color: '#fff', 
            border: 'none', 
            borderRadius: '4px',
            cursor: 'pointer' 
          }}>
            Edit Profile
          </button>
        </div>
      </div>
    </div>
  );
}

