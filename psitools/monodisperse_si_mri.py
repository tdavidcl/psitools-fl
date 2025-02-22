#
# Copyright 2020 Colin McNally, Sijme-Jan Paardekooper, Francesco Lovascio
#    colin@colinmcnally.ca, s.j.paardekooper@qmul.ac.uk, f.lovascio@qmul.ac.uk
#
#    This file is part of psitools.
#
#    psitools is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    psitools is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with psitools.  If not, see <https://www.gnu.org/licenses/>.
#
# Who: Colin and Francesco
import numpy as np
import scipy.linalg


class MonodisperseSIMRISolver:
    '''Monodispserse SI solver, in SJP form
    '''

    def __init__(self, taus, epsilon, c=0.05, eta=0.05*0.05):
        self.eta = eta
        self.c = c
        self.epsilon = epsilon
        self.taus = taus
        self.kappa = 1.0
        self.r0 = 1.0
        self.Omega = 1.0
        self.S = 3.0/2.0*self.Omega  # the right def for SJ notation
        self.rhog0 = 1.0
        self.By0 = 0.0
        self.Bz0 = 0.0

    def build_system_matrix(self, Kx, Kz):
        '''
        Version from SJ notation/notes

        Kx, Kz are non-dimensional, assume K = k eta r0
        taus stopping time of dust species, as in SJ eqs
        epsilon rho_d / rho_g, rho_d is integral(sigma)

        returns eigenvalue in format (oscillating part) + i*(growth rate)
        '''

        eta = self.eta
        c = self.c
        epsilon = self.epsilon
        taus = self.taus
        kappa = self.kappa
        r0 = self.r0
        Omega = self.Omega
        S = self.S
        rhog0 = self.rhog0
        By0 = self.By0
        Bz0 = self.Bz0

        fact_b_force = 1/(4*np.pi*rhog0)

        # convert input non-dimensional quantities to dimensional
        kx = Kx/(eta*r0)
        kz = Kz/(eta*r0)
        rhod0 = epsilon*rhog0

        self.kx = kx
        self.kz = kz

        # these are the single fluid limit of SJ forms
        J0 = 1.0/rhog0 * rhod0/(1.0 + kappa**2*taus**2)
        J1 = 1.0/rhog0 * rhod0 * taus/(1.0 + kappa**2*taus**2)

        vgx0 = 2.0*eta/(kappa) * J1/((1+J0)**2 + J1**2)
        vgy0 = -eta/Omega * (1.0+J0)/((1.0+J0)**2 + J1**2)
        # SJ u_x
        ux0 = 2.0*eta/(kappa) * (J1 - kappa*taus*(1+J0)) \
              / ((1 + kappa**2*taus**2)*((1+J0)**2 + J1**2))
        # SJ u_y
        uy0 = - eta/Omega * (1+J0+kappa*taus*J1) \
              / ((1 + kappa**2*taus**2)*((1+J0)**2 + J1**2))

        self.vgx0 = vgx0
        self.vgy0 = vgy0
        self.ux0 = ux0
        self.uy0 = uy0
        self.rhod0 = rhod0

        A = np.zeros((11, 11), dtype=np.cdouble)
        irhg = 0  # SJ rho_g^1
        ivgx = 1  # SJ v_{gx}^1
        ivgy = 2  # SJ v_{gy}^1
        ivgz = 3  # SJ v_{gz}^1
        irhd = 4  # SJ single dust sigma = epsilon
        iudx = 5  # SJ u_x^1,
        iudy = 6  # SJ u_y^1
        iudz = 7  # SJ u_z^1
        iBx = 8  # TDC B_x^1,
        iBy = 9  # TDC B_y^1
        iBz = 10  # TDC B_z^1
        self.irhg = irhg
        self.ivgx = ivgx
        self.ivgy = ivgy
        self.ivgz = ivgz
        self.irhd = irhd
        self.iudx = iudx
        self.iudy = iudy
        self.iudz = iudz
        self.iBx = iBx
        self.iBy = iBy
        self.iBz = iBz

        # rho_g
        A[irhg, irhg] = kx*vgx0
        A[irhg, ivgx] = kx
        A[irhg, ivgz] = kz
        # vgx
        A[ivgx, irhg] = kx*c**2
        A[ivgx, ivgx] = kx*vgx0 - 1.0j/rhog0*rhod0/taus
        A[ivgx, ivgy] = 2.0j*Omega
        A[ivgx, irhd] = 1.0j/rhog0*(ux0-vgx0)/taus
        A[ivgx, iudx] = 1.0j/rhog0*rhod0/taus
        #B field
        A[ivgx, iBx] = fact_b_force*(-Bz0 *kz)
        A[ivgx, iBy] = fact_b_force*(By0 *kx)
        A[ivgx, iBz] = fact_b_force*(Bz0 *kx)

        # vgy
        A[ivgy, ivgx] = 1.0j*(S-2.0*Omega)
        A[ivgy, ivgy] = kx*vgx0 - 1.0j/rhog0*rhod0/taus
        A[ivgy, irhd] = 1.0j/rhog0*(uy0-vgy0)/taus
        A[ivgy, iudy] = 1.0j/rhog0*rhod0/taus
        #B field
        A[ivgy, iBy] = fact_b_force*(-Bz0 *kz)

        # vgz
        A[ivgz, irhg] = kz*c**2
        A[ivgz, ivgz] = kx*vgx0 - 1.0j/rhog0*rhod0/taus
        A[ivgz, iudz] = 1.0j/rhog0*rhod0/taus
        #B field
        A[ivgz, iBy] = fact_b_force*(By0 *kz)

        # rho_d
        A[irhd, irhd] = kx*ux0
        A[irhd, iudx] = kx*rhod0
        A[irhd, iudz] = kz*rhod0
        # ux
        A[iudx, irhg] = - 1.0j/taus*(ux0-vgx0)
        A[iudx, ivgx] = 1.0j/taus
        A[iudx, iudx] = kx*ux0 - 1.0j/taus
        A[iudx, iudy] = 2.0j*Omega
        # vy
        A[iudy, irhg] = - 1.0j/taus*(uy0-vgy0)
        A[iudy, ivgy] = 1.0j/taus
        A[iudy, iudx] = 1.0j*(S-2.0*Omega)
        A[iudy, iudy] = kx*ux0 - 1.0j/taus
        # vz
        A[iudz, ivgz] = 1.0j/taus
        A[iudz, iudz] = kx*ux0 - 1.0j/taus

        # Bx
        A[iBx,iBx] = vgx0 * kx 
        A[iBx,ivgx] = -Bz0*kz

        #By
        A[iBy,ivgx] = By0*kx
        A[iBy,ivgy] = -Bz0*kz
        A[iBy,ivgz] = By0*kz
        A[iBy,iBx] = (-3.0j/2)*Omega
        A[iBy,iBy] = vgx0 * kx 

        #Bz
        A[iBz,iBz] = vgx0 * kx 
        A[iBz,ivgx] = Bz0*kx

        self.linear_system_matrix = A

    def add_turbulence(self, alpha=0):
        irhg = 0  # SJ rho_g^1
        ivgx = 1  # SJ v_{gx}^1
        ivgy = 2  # SJ v_{gy}^1
        ivgz = 3  # SJ v_{gz}^1
        irhd = 4  # SJ single dust sigma = epsilon
        # iudx = 5  # SJ u_x^1
        # iudy = 6  # SJ u_y^1
        # iudz = 7  # SJ u_z^1
        # eta = self.eta
        c = self.c
        # epsilon = self.epsilon
        taus = self.taus
        # kappa = self.kappa
        # r0 = self.r0
        # Omega = self.Omega
        # S = self.S
        rhog0 = self.rhog0
        kx = self.kx
        kz = self.kz
        ksq = kx*kx + kz*kz
        nu = alpha*c*c
        # vgx0 = self.vgx0
        # vgy0 = self.vgy0
        # ux0 = self.ux0
        # uy0 = self.uy0
        rhod0 = self.rhod0
        self.alpha = alpha
        D = ((1+taus+4*taus**2)*alpha*c**2)/((1+taus**2)**2)
        # rho_g
        # vgx
        self.linear_system_matrix[ivgx, ivgx] -= nu*((4/3)*kx**2 + kz**2)*1.0j
        self.linear_system_matrix[ivgx, ivgz] -= (1/3)*nu*kx*kz*1.0j
        # vgy
        self.linear_system_matrix[ivgy, ivgy] -= nu*(kz**2 + kx**2)*1.0j
        # vgz
        self.linear_system_matrix[ivgz, ivgx] -= 1/3*nu*kx*kz*1.0j
        self.linear_system_matrix[ivgz, ivgz] -= nu*(4/3*kz**2 + kx**2)*1.0j
        # rho_d
        self.linear_system_matrix[irhd, irhd] -= 1.0j*D*ksq
        self.linear_system_matrix[irhd, irhg] += 1.0j*D*ksq*rhod0/rhog0
        # ux
        # vy
        # vz

    def add_dust_pressure(self):
        """Adds dust pressure terms to system matrix.
        Will fail if turbulence has not been added"""
        irhd = 4  # SJ single dust sigma = epsilon
        iudx = 5  # SJ u_x^1,
        iudz = 7  # SJ u_z^1
        A = self.linear_system_matrix
        cdsquared = self.alpha*self.c**2/(1.0+self.taus**2)
        A[iudx, irhd] += self.kx*(cdsquared)  # dust pressure
        A[iudz, irhd] += self.kz*(cdsquared)  # dust pressure
        self.linear_system_matrix = A

    def solve_eigen(self):
        self.eigenvalues, self.eigenvectors = \
            scipy.linalg.eig(self.linear_system_matrix)

    def get_fastest_index(self):
        """Utility, the fastest growing eigenvalue is the most negative.
        """
        return np.argmax(self.eigenvalues.imag)

    def get_fastest_growth(self):
        return self.eigenvalues[self.get_fastest_index()]

    def get_fastest_growth_eigenvect(self):
        return self.eigenvectors[self.get_fastest_index()]
