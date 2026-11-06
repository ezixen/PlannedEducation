import { Mail } from 'lucide-react';
import { useI18n } from '../contexts/I18nContext';

interface MessageIconProps {
  unreadCount: number;
  onOpen: () => void;
}

/** Header-adjacent messages trigger (sits next to NotificationBell). */
export function MessageIcon({ unreadCount, onOpen }: MessageIconProps) {
  const { t } = useI18n();

  return (
    <button
      type="button"
      onClick={onOpen}
      aria-label={t('messages.icon_alt')}
      title={unreadCount > 0 ? `${t('messages.unread_count')}: ${unreadCount}` : t('messages.title')}
      style={{
        position: 'relative',
        background: 'var(--sidebar-bg)',
        border: '1px solid var(--border-color)',
        borderRadius: 'var(--radius-md)',
        padding: '0.45rem',
        cursor: 'pointer',
        color: 'var(--text-color)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transition: 'background-color 0.15s ease',
      }}
    >
      <Mail size={18} />
      {unreadCount > 0 && (
        <span
          style={{
            position: 'absolute',
            top: '-4px',
            right: '-4px',
            backgroundColor: '#ef4444',
            color: '#ffffff',
            fontSize: '0.7rem',
            fontWeight: 700,
            minWidth: '18px',
            height: '18px',
            borderRadius: '9999px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '0 4px',
            boxShadow: '0 1px 2px rgba(0,0,0,0.2)',
          }}
        >
          {unreadCount > 99 ? '99+' : unreadCount}
        </span>
      )}
    </button>
  );
}
