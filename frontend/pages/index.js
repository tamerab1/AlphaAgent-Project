import React from 'react';

export default function Home() {
  return (
    <div style={{
      backgroundColor: '#0d0e15',
      color: '#ffffff',
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      fontFamily: 'sans-serif'
    }}>
      <h1 style={{ color: '#9061f9', fontSize: '3rem', marginBottom: '10px' }}>AlphaAgent</h1>
      <p style={{ color: '#a0aec0', fontSize: '1.2rem' }}>AI Trading Portfolio Manager — Frontend Dashboard</p>
      <div style={{
        marginTop: '20px',
        padding: '10px 20px',
        borderRadius: '5px',
        backgroundColor: '#1a1c2a',
        border: '1px solid #2d3748',
        color: '#4ade80'
      }}>
        🟢 System Status: Active (Vercel Deployment Pipeline Ready)
      </div>
    </div>
  );
}