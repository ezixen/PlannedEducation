import { useState } from 'react';
import { Mail, ChevronRight } from 'lucide-react';
import { useI18n } from '../contexts/I18nContext';

interface MessageIconProps {
  unreadCount: number;
  onOpen: () => void;
}

export function MessageIcon({ unreadCount, onOpen }: MessageIconProps) {
  const { t } = useI18n();

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '1.5rem',
        left: '1.5rem',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
      }}
    >
      <button
        onClick={onOpen}
        aria-label={t('messages.icon_alt')}
        title={unreadCount > 0 ? `${t('messages.unread_count')}: ${unreadCount}` : t('messages.title')}
        style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          border: 'none',
          backgroundColor: 'var(--primary-color)',
          color: '#fff',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          fontSize: '1.5rem',
          transition: 'transform 0.2s',
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.transform = 'scale(1.05)'; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.transform = 'scale(1)'; }}
      >
        <Mail size={24} />
        {unreadCount > 0 && (
          <div
            style={{
              position: 'absolute',
              top: '4px',
              right: '4px',
              width: '20px',
              height: '20px',
              borderRadius: '50%',
              backgroundColor: 'var(--error-color)',
              color: '#fff',
              fontSize: '0.7rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 'bold',
              border: '2px solid #fff',
            }}
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </div>
        )}
      </button>
    </div>
  );
}