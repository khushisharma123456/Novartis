/**
 * Auth Logic for MedSafe
 * User object structure: { id, name, email, password, role }
 */

const STORAGE_USERS = 'medsafe_users';
const STORAGE_CURRENT_USER = 'medsafe_current_user';

export const Auth = {
    register: (name, email, password, role) => {
        const users = JSON.parse(localStorage.getItem(STORAGE_USERS) || '[]');

        // Check if email already exists
        if (users.find(u => u.email === email)) {
            return { success: false, message: 'Email already registered.' };
        }

        const newUser = {
            id: 'user_' + Date.now(),
            name,
            email,
            password, // In a real app, hash this!
            role
        };

        users.push(newUser);
        localStorage.setItem(STORAGE_USERS, JSON.stringify(users));
        return { success: true, user: newUser };
    },

    login: (email, password) => {
        const users = JSON.parse(localStorage.getItem(STORAGE_USERS) || '[]');
        const user = users.find(u => u.email === email && u.password === password);

        if (user) {
            localStorage.setItem(STORAGE_CURRENT_USER, JSON.stringify(user));
            // Also set role for sidebar easier access
            localStorage.setItem('userRole', user.role);
            return { success: true, user };
        }

        return { success: false, message: 'Invalid credentials.' };
    },

    logout: () => {
        localStorage.removeItem(STORAGE_CURRENT_USER);
        localStorage.removeItem('userRole');
        window.location.href = '/index.html';
    },

    getCurrentUser: () => {
        return JSON.parse(localStorage.getItem(STORAGE_CURRENT_USER));
    },

    requireAuth: () => {
        const user = Auth.getCurrentUser();
        if (!user) {
            window.location.href = '/login.html';
        }
        return user;
    }
};
