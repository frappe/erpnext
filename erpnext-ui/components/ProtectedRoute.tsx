import React from 'react';
import { Route, Redirect, RouteProps } from 'react-router-dom';
import { getCurrentUser } from '../utils/auth';

interface ProtectedRouteProps extends RouteProps {
  component: React.ComponentType<any>;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ component: Component, ...rest }) => (
  <Route
    {...rest}
    render={props =>
      getCurrentUser() ? (
        <Component {...props} />
      ) : (
        <Redirect to={{ pathname: '/login', state: { from: props.location } }} />
      )
    }
  />
);