import { useState, useEffect } from 'react';


export function TeacherClasses() {
  
  const [classes, setClasses] = useState<any[]>([]);
  const [newClassName, setNewClassName] = useState('');

  useEffect(() => {
    // Mock fetching classes
    setClasses([
      { id: 1, name: 'Calculus 101 - Fall 2026', students: 24 },
      { id: 2, name: 'AP History - Spring 2027', students: 30 }
    ]);
  }, []);

  

  const handleCreateClass = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClassName.trim()) return;
    
    const newClass = {
      id: Date.now(),
      name: newClassName,
      students: 0
    };
    setClasses([...classes, newClass]);
    setNewClassName('');
  };

  return (
    <div>
      <h1>Class Groupings</h1>
      <p style={{ color: 'gray', marginBottom: '2rem' }}>Manage your classes, enroll students, and configure IEP accommodations.</p>

      <div style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', marginBottom: '2rem' }}>
        <h3>Create New Class</h3>
        <form onSubmit={handleCreateClass} style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
          <input 
            type="text" 
            value={newClassName}
            onChange={(e) => setNewClassName(e.target.value)}
            placeholder="e.g., Biology 101" 
            style={{ flex: 1, padding: '0.75rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-color)', color: 'var(--text-color)' }}
          />
          <button type="submit" style={{ padding: '0.75rem 1.5rem', backgroundColor: 'var(--primary-color)', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
            Create
          </button>
        </form>
      </div>

      <div style={{ display: 'grid', gap: '1rem' }}>
        {classes.map(cls => (
          <div key={cls.id} style={{ padding: '1.5rem', backgroundColor: 'var(--sidebar-bg)', border: '1px solid var(--border-color)', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ margin: '0 0 0.5rem 0' }}>{cls.name}</h3>
              <p style={{ margin: 0, color: 'gray', fontSize: '0.9rem' }}>{cls.students} Enrolled Students</p>
            </div>
            <div>
              <button style={{ padding: '0.5rem 1rem', backgroundColor: 'transparent', color: 'var(--primary-color)', border: '1px solid var(--primary-color)', borderRadius: '4px', cursor: 'pointer' }}>
                Manage Roster
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
