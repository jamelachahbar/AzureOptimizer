import React, { useContext } from 'react';
import { Toolbar, Typography, IconButton, Button, Box, Container } from '@mui/material';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import { useTheme } from '@mui/material/styles';
import { ColorModeContext } from '../App'; // Adjust the import based on your file structure
import LogoutButton from './LogoutButton';

const Header: React.FC = () => {
  const theme = useTheme();
  const colorMode = useContext(ColorModeContext);

  return (

        <Container maxWidth={false} disableGutters>
          <Toolbar sx={{ justifyContent: 'space-between', width: '100%' }}>
            {/* //add logo from local folder CostOptTool\ui\frontend\public\ACOlogonew.png but make it smaller and to the left
            //add a button to go back to home page
            //add a button to change theme */}
           
            {/* add the logo */}
            <Typography variant="h6" component={Typography} fontWeight={
              'bold'} sx={{ color: 'primary' }
            }>
              ACO
            </Typography>
            {/* <img src="acologonewnobg.png" alt="ACO Logo" style={{ width: 50, height: 50 }} /> */}

            <Box sx={{display:{xs:'flex',md:'flex'}}}>

            {/* <Button variant="contained" color="primary" href="/">
                Home
              </Button> */}
            {/* <Button variant="contained" color="primary" href="/">
                About
              </Button>

              <Button variant="contained" color="primary" href="/">
                Contact
              </Button> */}

            </Box>

            <Box display="flex" alignItems="center">
              <IconButton onClick={colorMode.toggleColorMode} color="primary">
                {theme.palette.mode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
              </IconButton>
              <LogoutButton />
              {/* <Button variant="contained" color="primary" href="/">
                Log In - WIP
              </Button>  */}
            </Box>
          </Toolbar>
        </Container>

  );
};

export default Header;
