import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  FiMenu, 
  FiBell, 
  FiSearch, 
  FiUser,
  FiLogOut,
  FiSettings,
  FiChevronDown
} from 'react-icons/fi';
import './Navbar.css';

const Navbar = ({ toggleSidebar }) => {
  const { user, logout } = useAuth();
  const [showDropdown, setShowDropdown] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);

  const notifications = [
    { id: 1, title: 'Application Approved', message: 'Your loan application has been approved!', time: '2 hours ago', type: 'success' },
    { id: 2, title: 'Document Required', message: 'Please upload your income proof.', time: '5 hours ago', type: 'warning' },
    { id: 3, title: 'New Offer', message: 'You are eligible for a pre-approved loan.', time: '1 day ago', type: 'info' },
  ];

  return (
    <header className="navbar">
      <div className="navbar-left">
        <button className="navbar-toggle" onClick={toggleSidebar}>
          <FiMenu />
        </button>
        
        <div className="navbar-search">
          <FiSearch className="search-icon" />
          <input 
            type="text" 
            placeholder="Search applications, documents..." 
            className="search-input"
          />
        </div>
      </div>

      <div className="navbar-right">
        {/* Notifications */}
        <div className="navbar-item">
          <button 
            className="navbar-icon-btn"
            onClick={() => setShowNotifications(!showNotifications)}
          >
            <FiBell />
            <span className="notification-badge">3</span>
          </button>
          
          {showNotifications && (
            <div className="dropdown-menu notifications-menu">
              <div className="dropdown-header">
                <h4>Notifications</h4>
                <button className="mark-read">Mark all as read</button>
              </div>
              <div className="notifications-list">
                {notifications.map((notification) => (
                  <div key={notification.id} className={`notification-item ${notification.type}`}>
                    <div className="notification-dot"></div>
                    <div className="notification-content">
                      <span className="notification-title">{notification.title}</span>
                      <span className="notification-message">{notification.message}</span>
                      <span className="notification-time">{notification.time}</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="dropdown-footer">
                <a href="/notifications">View all notifications</a>
              </div>
            </div>
          )}
        </div>

        {/* User Menu */}
        <div className="navbar-item">
          <button 
            className="user-menu-btn"
            onClick={() => setShowDropdown(!showDropdown)}
          >
            <div className="user-avatar">
              {user?.name?.charAt(0) || 'U'}
            </div>
            <div className="user-info">
              <span className="user-name">{user?.name || 'User'}</span>
              <span className="user-role">{user?.role || 'Customer'}</span>
            </div>
            <FiChevronDown className={`dropdown-arrow ${showDropdown ? 'open' : ''}`} />
          </button>

          {showDropdown && (
            <div className="dropdown-menu user-dropdown">
              <div className="dropdown-user-header">
                <div className="user-avatar large">
                  {user?.name?.charAt(0) || 'U'}
                </div>
                <div>
                  <span className="user-name">{user?.name || 'User'}</span>
                  <span className="user-email">{user?.email || 'user@email.com'}</span>
                </div>
              </div>
              <div className="dropdown-divider"></div>
              <a href="/profile" className="dropdown-item">
                <FiUser /> My Profile
              </a>
              <a href="/settings" className="dropdown-item">
                <FiSettings /> Settings
              </a>
              <div className="dropdown-divider"></div>
              <button className="dropdown-item logout" onClick={logout}>
                <FiLogOut /> Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Navbar;
