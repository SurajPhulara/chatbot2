import React, { useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import { createBrowserRouter, RouterProvider, useNavigate } from 'react-router-dom';
import App from './App';
import './index.css';
import { v4 as uuidv4 } from 'uuid';

export const generateUniqueId = () => uuidv4();


const RedirectToUniqueId = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Check if a user ID is present in the URL
    const urlPath = window.location.pathname;
    const pathParts = urlPath.split('/');
    const existingUserId = pathParts[1];

    if (!existingUserId || existingUserId === '') {
      // Generate a new unique ID and redirect
      const newUserId = generateUniqueId();
      navigate(`/${newUserId}`, { replace: true });
    }
  }, [navigate]);

  return null;
};

const router = createBrowserRouter([
  {
    path: "/",
    element: <RedirectToUniqueId />,
  },
  {
    path: "/:userId",
    element: <App />,
  },
]);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
