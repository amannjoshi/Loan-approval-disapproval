import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  FiHome, 
  FiFileText, 
  FiCheckCircle, 
  FiShield, 
  FiSettings,
  FiHelpCircle,
  FiX
} from 'react-icons/fi';
import './Sidebar.css';

const Sidebar = ({ isOpen, toggleSidebar }) => {
  const menuItems = [
    { path: '/dashboard', icon: <FiHome />, label: 'Dashboard' },
    { path: '/apply', icon: <FiFileText />, label: 'Apply for Loan' },
    { path: '/status', icon: <FiCheckCircle />, label: 'Application Status' },
    { path: '/privacy', icon: <FiShield />, label: 'Privacy Demo' },
  ];

  const bottomMenuItems = [
    { path: '/settings', icon: <FiSettings />, label: 'Settings' },
    { path: '/help', icon: <FiHelpCircle />, label: 'Help & Support' },
  ];

  return (
    <>
      {/* Overlay for mobile */}
      <div 
        className={`sidebar-overlay ${isOpen ? 'active' : ''}`}
        onClick={toggleSidebar}
      />
      
      <aside className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
        {/* Logo Section */}
        <div className="sidebar-header">
          <div className="logo">
            <div className="logo-icon">
              <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect width="40" height="40" rx="8" fill="url(#gradient)" />
                <path d="M12 28V12H16L20 20L24 12H28V28H24V18L20 26H20L16 18V28H12Z" fill="white"/>
                <defs>
                  <linearGradient id="gradient" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#1a73e8"/>
                    <stop offset="1" stopColor="#0d47a1"/>
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <div className="logo-text">
              <span className="logo-title">LoanWise</span>
              <span className="logo-subtitle">Smart Approvals</span>
            </div>
          </div>
          <button className="sidebar-close" onClick={toggleSidebar}>
            <FiX />
          </button>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          <div className="nav-section">
            <span className="nav-section-title">Main Menu</span>
            <ul className="nav-list">
              {menuItems.map((item) => (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    className={({ isActive }) => 
                      `nav-link ${isActive ? 'active' : ''}`
                    }
                  >
                    <span className="nav-icon">{item.icon}</span>
                    <span className="nav-label">{item.label}</span>
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>

          <div className="nav-section">
            <span className="nav-section-title">Support</span>
            <ul className="nav-list">
              {bottomMenuItems.map((item) => (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    className={({ isActive }) => 
                      `nav-link ${isActive ? 'active' : ''}`
                    }
                  >
                    <span className="nav-icon">{item.icon}</span>
                    <span className="nav-label">{item.label}</span>
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        </nav>

        {/* Promo Card */}
        <div className="sidebar-promo">
          <div className="promo-content">
            <h4>Need Help?</h4>
            <p>Contact our support team for assistance with your application.</p>
            <button className="btn btn-primary btn-sm">Contact Support</button>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
