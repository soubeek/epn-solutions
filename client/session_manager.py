"""
Gestionnaire de session - Gestion de l'écran, déconnexion, notifications
Compatible Linux (X11) et Windows
"""

import os
import sys
import subprocess
import logging
import config


class SessionManager:
    """
    Gère les opérations système (lock/unlock, logout, notifications)
    """

    def __init__(self):
        self.logger = logging.getLogger('SessionManager')
        self.logger.info(f"SessionManager initialisé pour {config.OS_TYPE}")

    def lock_screen(self):
        """Verrouille l'écran"""
        self.logger.info("Verrouillage de l'écran")

        try:
            if config.IS_LINUX:
                self._lock_screen_linux()
            elif config.IS_WINDOWS:
                self._lock_screen_windows()
            else:
                self.logger.warning(f"Verrouillage non supporté sur {config.OS_TYPE}")
        except Exception as e:
            self.logger.error(f"Erreur verrouillage écran: {e}")

    def unlock_screen(self):
        """Déverrouille l'écran"""
        self.logger.info("Déverrouillage de l'écran")
        # Note: Le déverrouillage automatique peut nécessiter des privilèges élevés
        # Sur la plupart des systèmes, c'est géré par l'authentification utilisateur

    def _lock_screen_linux(self):
        """Verrouille l'écran sur Linux"""
        # Détecter le gestionnaire de session
        desktop = os.getenv('XDG_CURRENT_DESKTOP', '').lower()
        session_type = os.getenv('XDG_SESSION_TYPE', '').lower()

        commands = [
            # Essayer d'abord avec loginctl (systemd)
            ['loginctl', 'lock-session'],
            # GNOME/Unity
            ['gnome-screensaver-command', '-l'],
            ['dbus-send', '--type=method_call', '--dest=org.gnome.ScreenSaver',
             '/org/gnome/ScreenSaver', 'org.gnome.ScreenSaver.Lock'],
            # KDE
            ['qdbus', 'org.freedesktop.ScreenSaver', '/ScreenSaver', 'Lock'],
            ['dbus-send', '--type=method_call', '--dest=org.freedesktop.ScreenSaver',
             '/ScreenSaver', 'org.freedesktop.ScreenSaver.Lock'],
            # XFCE
            ['xflock4'],
            # Cinnamon
            ['cinnamon-screensaver-command', '-l'],
            # MATE
            ['mate-screensaver-command', '-l'],
            # i3, dwm, etc.
            ['xdg-screensaver', 'lock'],
            ['slock'],
            ['xtrlock']
        ]

        for cmd in commands:
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=2)
                self.logger.info(f"Écran verrouillé avec: {cmd[0]}")
                return
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue

        self.logger.warning("Aucune commande de verrouillage n'a fonctionné")

    def _lock_screen_windows(self):
        """Verrouille l'écran sur Windows"""
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            self.logger.info("Écran verrouillé (Windows)")
        except Exception as e:
            self.logger.error(f"Erreur verrouillage Windows: {e}")

    def logout_user(self):
        """Déconnecte l'utilisateur"""
        self.logger.info("Déconnexion de l'utilisateur")

        try:
            if config.IS_LINUX:
                self._logout_linux()
            elif config.IS_WINDOWS:
                self._logout_windows()
        except Exception as e:
            self.logger.error(f"Erreur déconnexion: {e}")

    def _logout_linux(self):
        """Déconnecte l'utilisateur sur Linux"""
        commands = [
            # systemd
            ['loginctl', 'terminate-user', os.getenv('USER')],
            # GNOME
            ['gnome-session-quit', '--logout', '--no-prompt'],
            # KDE
            ['qdbus', 'org.kde.ksmserver', '/KSMServer', 'logout', '0', '0', '0'],
            # XFCE
            ['xfce4-session-logout', '--logout'],
            # Cinnamon
            ['cinnamon-session-quit', '--logout', '--no-prompt'],
            # MATE
            ['mate-session-save', '--logout'],
            # Fallback brutal
            ['pkill', '-u', os.getenv('USER')]
        ]

        for cmd in commands:
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=2)
                self.logger.info(f"Déconnexion avec: {cmd[0]}")
                return
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue

        self.logger.warning("Aucune commande de déconnexion n'a fonctionné")

    def _logout_windows(self):
        """Déconnecte l'utilisateur sur Windows"""
        try:
            subprocess.run(['shutdown', '/l'], check=True)
            self.logger.info("Déconnexion Windows")
        except Exception as e:
            self.logger.error(f"Erreur déconnexion Windows: {e}")

    def show_warning(self, title, message):
        """Affiche une notification d'avertissement"""
        self.logger.info(f"Notification: {title} - {message}")

        try:
            if config.IS_LINUX:
                self._show_notification_linux(title, message)
            elif config.IS_WINDOWS:
                self._show_notification_windows(title, message)
        except Exception as e:
            self.logger.error(f"Erreur notification: {e}")

    def _show_notification_linux(self, title, message):
        """Affiche une notification sur Linux"""
        commands = [
            # notify-send (le plus courant)
            ['notify-send', '-u', 'critical', '-t', '5000', title, message],
            # zenity
            ['zenity', '--warning', '--text', f"{title}\n\n{message}"],
            # kdialog
            ['kdialog', '--title', title, '--passivepopup', message, '5'],
            # xmessage (fallback)
            ['xmessage', '-center', f"{title}\n\n{message}"]
        ]

        for cmd in commands:
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.logger.info(f"Notification envoyée avec: {cmd[0]}")
                return
            except FileNotFoundError:
                continue

        # Fallback: afficher dans le terminal
        print(f"\n{'='*60}")
        print(f"  {title.upper()}")
        print(f"{'='*60}")
        print(f"  {message}")
        print(f"{'='*60}\n")

    def _show_notification_windows(self, title, message):
        """Affiche une notification sur Windows"""
        try:
            # Méthode 1 : Toast notification (Windows 10/11)
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(
                    title,
                    message,
                    icon_path=None,
                    duration=5,
                    threaded=True
                )
                self.logger.info("Notification toast Windows envoyée")
                return
            except ImportError:
                pass
            except Exception as e:
                self.logger.warning(f"Échec toast notification: {e}")

            # Méthode 2 : Message box avec ctypes
            try:
                import ctypes
                MB_OK = 0x0
                MB_ICONWARNING = 0x30
                MB_TOPMOST = 0x40000
                ctypes.windll.user32.MessageBoxW(
                    0,
                    message,
                    title,
                    MB_OK | MB_ICONWARNING | MB_TOPMOST
                )
                self.logger.info("MessageBox Windows affichée")
                return
            except Exception as e:
                self.logger.warning(f"Échec MessageBox: {e}")

            # Méthode 3 : msg.exe (envoi à tous les utilisateurs)
            try:
                subprocess.Popen(
                    ['msg', '*', f"{title}\n\n{message}"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.logger.info("msg.exe Windows envoyé")
                return
            except Exception as e:
                self.logger.warning(f"Échec msg.exe: {e}")

            # Fallback : PowerShell avec ballon notification
            try:
                ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms
$notification = New-Object System.Windows.Forms.NotifyIcon
$notification.Icon = [System.Drawing.SystemIcons]::Information
$notification.BalloonTipTitle = "{title}"
$notification.BalloonTipText = "{message}"
$notification.Visible = $true
$notification.ShowBalloonTip(5000)
Start-Sleep -Seconds 6
$notification.Dispose()
'''
                subprocess.Popen(
                    ['powershell', '-WindowStyle', 'Hidden', '-Command', ps_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.logger.info("PowerShell balloon notification envoyée")
                return
            except Exception as e:
                self.logger.warning(f"Échec PowerShell notification: {e}")

        except Exception as e:
            self.logger.error(f"Erreur notification Windows: {e}")

        # Fallback terminal
        print(f"\n{'='*60}")
        print(f"  {title.upper()}")
        print(f"{'='*60}")
        print(f"  {message}")
        print(f"{'='*60}\n")

    def is_screen_locked(self):
        """Vérifie si l'écran est verrouillé"""
        if config.IS_LINUX:
            return self._is_screen_locked_linux()
        elif config.IS_WINDOWS:
            return self._is_screen_locked_windows()
        return False

    def _is_screen_locked_linux(self):
        """Vérifie si l'écran est verrouillé sur Linux"""
        # Vérifier avec loginctl
        try:
            result = subprocess.run(['loginctl', 'show-session', '-p', 'LockedHint'],
                                  capture_output=True, text=True, timeout=1)
            return 'yes' in result.stdout.lower()
        except:
            pass

        # Vérifier les screensavers
        screensavers = [
            ['gnome-screensaver-command', '-q'],
            ['xscreensaver-command', '-time'],
        ]

        for cmd in screensavers:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=1)
                if 'active' in result.stdout.lower() or 'locked' in result.stdout.lower():
                    return True
            except:
                continue

        return False

    def _is_screen_locked_windows(self):
        """Vérifie si l'écran est verrouillé sur Windows"""
        try:
            import ctypes
            # Cette méthode n'est pas fiable à 100% sous Windows
            # Nécessite généralement une approche plus complexe
            return False
        except:
            return False
